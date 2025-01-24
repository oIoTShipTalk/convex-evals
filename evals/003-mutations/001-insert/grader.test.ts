import { expect, test } from "vitest";
import { responseClient, compareSchema, compareFunctionSpec } from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});

test("insert user success", async () => {
  const result = await responseClient.mutation(anyApi.index.insertUser, {
    email: "jordan@convex.dev",
    name: "Jordan",
    age: 23,
  });
  expect(result).toBeTypeOf("string");
});

test("insert user error", async () => {
  let error: any = undefined;
  try {
    await responseClient.mutation(anyApi.index.insertUser, {
      email: "jordan@convex.dev",
      name: "Jordan",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");
});
