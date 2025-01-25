import { ConvexClient } from "convex/browser";
import { expect } from "vitest";

const responsePort = process.env.CONVEX_PORT;
if (!responsePort) {
  throw new Error("CONVEX_PORT is not set");
}

const answerPort = process.env.CONVEX_ANSWER_PORT;

export const responseClient = new ConvexClient(
  `http://0.0.0.0:${responsePort}`,
);

const adminKey =
  "0135d8598650f8f5cb0f30c34ec2e2bb62793bc28717c8eb6fb577996d50be5f4281b59181095065c5d0f86a2c31ddbe9b597ec62b47ded69782cd";
export const responseAdminClient = new ConvexClient(
  `http://0.0.0.0:${responsePort}`,
);
(responseAdminClient as any).setAdminAuth(adminKey);

let answerAdminClient: ConvexClient | null = null;
if (answerPort) {
  answerAdminClient = new ConvexClient(`http://0.0.0.0:${answerPort}`);
  (answerAdminClient as any).setAdminAuth(adminKey);
}

export async function getSchema(adminClient: any) {
  const result = await adminClient.query("_system/frontend/getSchemas" as any, {
    componentId: null,
  });
  if (!result.active) {
    return null;
  }
  const schema = JSON.parse(result.active);
  schema.tables.sort((a: any, b: any) =>
    a.tableName.localeCompare(b.tableName),
  );
  return schema;
}

/**
 * Insert the given documents into a table.
 */
export async function addDocuments(
  adminClient: any,
  table: string,
  documents: any[],
): Promise<void> {
  const result = await adminClient.mutation("_system/frontend/addDocument", {
    table,
    documents,
  });
  if (!result.success) {
    throw new Error(result.error);
  }
}

/**
 * List the given table, returning the results in ascending creation time order.
 */
export async function listTable(
  adminClient: any,
  table: string,
  limit: number = 32,
): Promise<any[]> {
  const result: any[] = await adminClient.query(
    "_system/frontend/listTableScan",
    {
      table,
      limit,
    },
  );
  result.reverse();
  return result;
}

export async function compareSchema(skip: (note?: string) => void) {
  if (!answerAdminClient) {
    skip("Answer backend not available");
    return;
  }
  const responseSchema = await getSchema(responseAdminClient);
  const answerSchema = await getSchema(answerAdminClient);
  expect(responseSchema).toEqual(answerSchema);
}

async function getFunctionSpec(adminClient: any) {
  const result = await adminClient.query(
    "_system/cli/modules:apiSpec" as any,
    {},
  );
  return result;
}

export async function compareFunctionSpec(skip: (note?: string) => void) {
  if (!answerAdminClient) {
    skip("Answer backend not available");
    return;
  }
  const responseFunctionSpec = await getFunctionSpec(responseAdminClient);
  const answerFunctionSpec = await getFunctionSpec(answerAdminClient);
  expect(responseFunctionSpec).toEqual(answerFunctionSpec);
}
