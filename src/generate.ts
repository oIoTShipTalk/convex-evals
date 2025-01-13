import { join } from "path";
import { readFile, mkdir, writeFile } from "fs/promises";
import { Anthropic } from "@anthropic-ai/sdk";
import { load } from "cheerio";

const SYSTEM_PROMPT =
  "You are convexbot, a highly advanced AI programmer specialized in creating backend systems using Convex.";

const USER_PROMPT_TEMPLATE = `
Your task is to generate a Convex backend based on the following task description:
<task_description>
%s
</task_description>

Before writing any code, analyze the task and think through your approach. Use <analysis> tags to show your thought process, covering the following areas:

1. Summarize the task requirements
2. List out the main components needed for the backend
3. Design the public API:
   - List each function with its purpose and expected arguments
4. Plan the schema design (if needed):
   - List each table with its fields and types
5. Outline background processing requirements (if any):

After your analysis, generate the necessary files for a Convex backend that implements the requested functionality. 

<guidelines>
  <file_structure>
   - You can write to \`package.json\` and any files within the \`convex/\` folder.
   - Do NOT write to the \`convex/_generated\` folder. You can assume that \`npx convex dev\` will populate this folder.
   - Use <file path="file_path" /> syntax to output each file.
   - Always start with a \`package.json\` file.
   - Use Convex version "^1.17.4".
  </file_structure>

  <general_coding_standards>
    - Use 2 spaces for code indentation.
    - Ensure your code is clear, efficient, concise, and innovative.
    - Maintain a friendly and approachable tone in any comments or documentation.    
  </general_coding_standards>

  <guidelines>
    <function_guidelines>
        <new_function_syntax>
            ALWAYS use the new function syntax for Convex functions. For example:
            \`\`\`typescript
            import { query } from "./_generated/server";
            import { v } from "convex/values";
            export const f = query({
                args: {},
                returns: v.null(),
                handler: async (ctx, args) => {
                // Function body
                },
            });
            \`\`\`
        </new_function_syntax>
        <http_endpoint_syntax>
            HTTP endpoints are defined in \`convex/http.ts\` and require an \`httpAction\` decorator. For example:
            \`\`\`typescript
            import { httpRouter } from "convex/server";
            import { httpAction } from "./_generated/server";
            const http = httpRouter();
            http.route({
                path: "/echo",
                method: "POST",
                handler: httpAction(async (ctx, req) => {
                const body = await req.bytes();
                return new Response(body, { status: 200 });
                }),
            });
            \`\`\`
            For simple HTTP routes, define the handler directly within the route definition.
        </http_endpoint_syntax>        
        <function_calling>
            - Use \`ctx.runQuery\` to call a query from a mutation or action.
            - Use \`ctx.runMutation\` to call a mutation from an action.
            - Try to use as few calls from actions to queries and mutations as possible. Queries
              and mutations are transactions, so splitting logic up into multiple calls introduces
              the risk of race conditions.
            - Use \`ctx.runAction\` to call an action from an action. ONLY call an action from another
              action if you need to cross runtimes (e.g. from V8 to Node). Otherwise, pull out the
              shared code into a helper async function and call that directly instead.        
            - All of these calls take in a \`FunctionReference\` Do NOT try to pass the callee 
              function directly into one of these calls.
        </function_calling>
        <function_references>
            - Function references are pointers to registered Convex functions.
            - Use the \`api\` object defined by the framework in \`convex/_generated/api.ts\` to call public functions
              registered with \`query\`, \`mutation\`, or \`action\`.
            - Use the \`internal\` object defined by the framework in \`convex/_generated/api.ts\` to call internal 
              (or private) functions registered with \`internalQuery\`, \`internalMutation\`, or \`internalAction\`.              
            - Convex uses file-based routing, so a public function defined in \`convex/public.ts\` named \`f\` has
              a function reference of \`api.public.f\`.
            - A private function defined in \`convex/private.ts\` named \`g\` has a function reference of 
              \`internal.private.g\`.
            - Functions can also registered within directories nested within the \`convex/\` folder. For example,
              a public function \`h\` defined in \`convex/messages/access.ts\` has a function reference of
              \`api.messages.access.h\`.
        </function_references>
        <api_design>
            - Convex uses file-based routing, so thoughtfully organize files with public query, mutation,
                or action functions within the \`convex/\` directory.
            - Use \`query\`, \`mutation\`, and \`action\` to define public functions.
            - Use \`internalQuery\`, \`internalMutation\`, and \`internalAction\` to define private, internal functions.
        </api_design>
    </function_guidelines>
    <schema_guidelines>
        - Always define your schema in \`convex/schema.ts\`.
        - Always import the schema definition functions from \`convex/server\`:
          \`\`\`typescript
          import { defineSchema, defineTable } from "convex/server";
          import { v } from "convex/values";

          export default defineSchema({
            exampleTable: defineTable({
              exampleField: v.string(),
            }),
          });
          \`\`\`        
    </schema_guidelines>
    <query_guidelines>
        - Do NOT use \`filter\` in queries. Instead, define an index in the schema and use \`withIndex\` instead.
        - Convex queries do NOT support \`.delete()\`. Instead, \`.collect()\` the results, iterate over them, and call \`ctx.db.delete(row._id)\` on each result.
    </query_guidelines>
    <mutation_guidelines>
        - Use \`ctx.db.replace\` to fully replace an existing document. This method will throw an error if the document does not exist.
        - Use \`ctx.db.patch\` to shallow merge updates into an existing document. This method will throw an error if the document does not exist.
    </mutation_guidelines>
</guidelines>

Begin your response with your thought process, then proceed to generate the necessary files for the Convex backend.
`;

interface GenerateOptions {
  inputDir: string;
  outputRoot: string;
  client: Anthropic;
}

export async function generateTest({
  inputDir,
  outputRoot,
  client,
}: GenerateOptions) {
  const start = Date.now();

  const prompt = await readFile(join(inputDir, "PROMPT.txt"), "utf-8");
  const userPrompt = USER_PROMPT_TEMPLATE.replace("%s", prompt);

  const message = await client.messages.create({
    model: "claude-3-5-sonnet-latest",
    system: SYSTEM_PROMPT,
    messages: [
      { role: "user", content: [{ type: "text", text: userPrompt }] },
      { role: "assistant", content: [{ type: "text", text: "<analysis>" }] },
    ],
    max_tokens: 4096,
  });

  if (message.content.length !== 1 || message.content[0].type !== "text")
    throw new Error(
      `Message content is not text: ${JSON.stringify(message.content)}`
    );

  const $ = load("<analysis>" + message.content[0].text);
  const projectDir = join(outputRoot, "project");
  await mkdir(projectDir, { recursive: true });

  let generated = 0;
  for (const fileTag of $("file").toArray()) {
    const path = $(fileTag).attr("path");
    if (!path) throw new Error("File path is not set");

    console.log(`Writing ${path}...`);
    const absFilePath = join(projectDir, path);

    if (!absFilePath.startsWith(projectDir))
      throw new Error(
        `File path ${absFilePath} is not underneath ${projectDir}`
      );

    await mkdir(join(absFilePath, ".."), { recursive: true });
    const content = $(fileTag).text().trim();
    await writeFile(absFilePath, content);
    generated += content.length;
  }

  console.log(
    `Generated ${generated} bytes in ${
      (Date.now() - start) / 1000
    } seconds to ${outputRoot}`
  );
}
