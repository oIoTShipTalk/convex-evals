import { expect, test } from "vitest";
import {
  responseAdminClient,
  responseClient,
  compareSchema,
  compareFunctionSpec,
} from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async ({ skip }) => {
  await compareSchema(skip);
});

test("compare function spec", async ({ skip }) => {
  await compareFunctionSpec(skip);
});

test("empty public query", async () => {
  const result = await responseClient.query(anyApi.index.emptyPublicQuery, {});
  expect(result).toBe(null);

  let error: any = undefined;
  try {
    await responseClient.query(anyApi.index.emptyPublicQuery, {
      arg: "test",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");

  error = undefined;
  try {
    await responseClient.mutation(anyApi.index.emptyPublicQuery, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();

  error = undefined;
  try {
    await responseClient.action(anyApi.index.emptyPublicQuery, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
});

test("empty public mutation", async () => {
  const result = await responseClient.mutation(
    anyApi.index.emptyPublicMutation,
    {},
  );
  expect(result).toBe(null);

  let error: any = undefined;
  try {
    await responseClient.mutation(anyApi.index.emptyPublicMutation, {
      arg: "test",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");

  error = undefined;
  try {
    await responseClient.query(anyApi.index.emptyPublicMutation, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();

  error = undefined;
  try {
    await responseClient.action(anyApi.index.emptyPublicMutation, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
});

test("empty public action", async () => {
  const result = await responseClient.action(
    anyApi.index.emptyPublicAction,
    {},
  );
  expect(result).toBe(null);

  let error: any = undefined;
  try {
    await responseClient.action(anyApi.index.emptyPublicAction, {
      arg: "test",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");

  error = undefined;
  try {
    await responseClient.query(anyApi.index.emptyPublicAction, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();

  error = undefined;
  try {
    await responseClient.mutation(anyApi.index.emptyPublicAction, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
});

test("empty private query", async () => {
  let error: any = undefined;
  try {
    await responseClient.query(anyApi.index.emptyPrivateQuery, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("Could not find public function");

  const result = await responseAdminClient.query(
    anyApi.index.emptyPrivateQuery,
    {},
  );
  expect(result).toBe(null);
});

test("empty private mutation", async () => {
  let error: any = undefined;
  try {
    await responseClient.mutation(anyApi.index.emptyPrivateMutation, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("Could not find public function");

  const result = await responseAdminClient.mutation(
    anyApi.index.emptyPrivateMutation,
    {},
  );
  expect(result).toBe(null);
});

test("empty private action", async () => {
  let error: any = undefined;
  try {
    await responseClient.action(anyApi.index.emptyPrivateAction, {});
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("Could not find public function");

  const result = await responseAdminClient.action(
    anyApi.index.emptyPrivateAction,
    {},
  );
  expect(result).toBe(null);
});
