import { expect, test } from "vitest";
import {
  responseAdminClient,
  responseClient,
  compareFunctionSpec,
  compareSchema,
} from "../../../grader";
import { anyApi } from "convex/server";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});
