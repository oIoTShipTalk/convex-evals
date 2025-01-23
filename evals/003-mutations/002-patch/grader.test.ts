import { expect, test } from "vitest";
import { client, compareSchema, compareFunctionSpec } from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});

test("update user error", async () => {
  let error: any = undefined;
  try {
    await client.mutation(anyApi.index.updateUserEmail, {
      email: "jordan@convex.dev",
      name: "Jordan",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");
});
