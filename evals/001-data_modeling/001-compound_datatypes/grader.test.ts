import { expect, test } from "vitest";
import {
  responseAdminClient,
  responseClient,
  compareSchema,
  compareFunctionSpec,
} from "../../../grader";

test("compare schema", async () => {
  await compareSchema();
});

test("compare function spec", async () => {
  await compareFunctionSpec();
});
