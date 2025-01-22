import { test } from "vitest";
import { compareSchema, compareFunctionSpec } from "../../../grader";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});
