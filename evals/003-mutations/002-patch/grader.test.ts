import { expect, test } from "vitest";
import {
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

test("update user error", async () => {
  let error: any = undefined;
  try {
    await responseClient.mutation(anyApi.index.updateUserEmail, {
      email: "jordan@convex.dev",
      name: "Jordan",
    });
  } catch (e) {
    error = e;
  }
  expect(error).toBeDefined();
  expect(error.toString()).toContain("ArgumentValidationError");
});
