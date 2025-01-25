import { expect, test } from "vitest";
import {
  responseAdminClient,
  responseClient,
  compareFunctionSpec,
  compareSchema,
} from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async ({ skip }) => {
  await compareSchema(skip);
});

test("compare function spec", async ({ skip }) => {
  await compareFunctionSpec(skip);
});
