import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  CallToolRequestSchema,
  CompleteRequestSchema,
  GetPromptRequestSchema,
  ListPromptsRequestSchema,
  ListResourcesRequestSchema,
  ListResourceTemplatesRequestSchema,
  ListToolsRequestSchema,
  LoggingMessageNotificationSchema,
  ReadResourceRequestSchema,
  SubscribeRequestSchema,
  UnsubscribeRequestSchema,
  ResourceUpdatedNotificationSchema,
  ServerCapabilities,
} from "@modelcontextprotocol/sdk/types.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { z } from "zod/v4";
import type { ListToolsResult } from "@modelcontextprotocol/sdk/types.js";

const LooseListToolsResultSchema = z
  .object({
    _meta: z.record(z.string(), z.unknown()).optional(),
    nextCursor: z.string().optional(),
    tools: z.array(z.record(z.string(), z.unknown())),
  })
  .catchall(z.unknown());

type LooseListToolsResult = z.infer<typeof LooseListToolsResultSchema>;

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null && !Array.isArray(value);
};

const sanitizeToolOutputSchemas = (
  result: LooseListToolsResult,
): ListToolsResult => {
  return {
    ...result,
    tools: result.tools.map((tool) => {
      const outputSchema = tool.outputSchema;

      if (outputSchema === undefined) {
        return tool;
      }

      if (!isRecord(outputSchema)) {
        const toolWithoutOutputSchema = { ...tool };
        delete toolWithoutOutputSchema.outputSchema;

        return toolWithoutOutputSchema;
      }

      if (outputSchema.type === "object") {
        return tool;
      }

      return {
        ...tool,
        outputSchema: {
          ...outputSchema,
          type: "object",
        },
      };
    }),
  } as ListToolsResult;
};

export const proxyServer = async ({
  server,
  client,
  serverCapabilities,
}: {
  server: Server;
  client: Client;
  serverCapabilities: ServerCapabilities;
}) => {
  if (serverCapabilities?.logging) {
    server.setNotificationHandler(
      LoggingMessageNotificationSchema,
      async (args) => {
        return client.notification(args);
      },
    );
  }

  if (serverCapabilities?.prompts) {
    server.setRequestHandler(GetPromptRequestSchema, async (args) => {
      return client.getPrompt(args.params);
    });

    server.setRequestHandler(ListPromptsRequestSchema, async (args) => {
      return client.listPrompts(args.params);
    });
  }

  if (serverCapabilities?.resources) {
    server.setRequestHandler(ListResourcesRequestSchema, async (args) => {
      return client.listResources(args.params);
    });

    server.setRequestHandler(
      ListResourceTemplatesRequestSchema,
      async (args) => {
        return client.listResourceTemplates(args.params);
      },
    );

    server.setRequestHandler(ReadResourceRequestSchema, async (args) => {
      return client.readResource(args.params);
    });

    if (serverCapabilities?.resources.subscribe) {
      server.setNotificationHandler(
          ResourceUpdatedNotificationSchema,
          async (args) => {
            return client.notification(args);
          },
      );

      server.setRequestHandler(SubscribeRequestSchema, async (args) => {
        return client.subscribeResource(args.params);
      });

      server.setRequestHandler(UnsubscribeRequestSchema, async (args) => {
        return client.unsubscribeResource(args.params);
      });
    }
  }

  if (serverCapabilities?.tools) {
    server.setRequestHandler(CallToolRequestSchema, async (args) => {
      return client.callTool(args.params);
    });

    server.setRequestHandler(ListToolsRequestSchema, async (args) => {
      const result = await client.request(
        {
          method: "tools/list",
          params: args.params,
        },
        LooseListToolsResultSchema,
      );

      return sanitizeToolOutputSchemas(result);
    });
  }

  if (serverCapabilities?.completions) {
    server.setRequestHandler(CompleteRequestSchema, async (args) => {
      return client.complete(args.params);
    });
  }
};
