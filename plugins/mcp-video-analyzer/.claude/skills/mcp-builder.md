---
name: mcp-builder
description: Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
---

# MCP Server Development Guide

## Overview

Create MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. The quality of an MCP server is measured by how well it enables LLMs to accomplish real-world tasks.

---

# Process

## High-Level Workflow

Creating a high-quality MCP server involves four main phases:

### Phase 1: Deep Research and Planning

#### 1.1 Understand Modern MCP Design

**API Coverage vs. Workflow Tools:**
Balance comprehensive API endpoint coverage with specialized workflow tools. Workflow tools can be more convenient for specific tasks, while comprehensive coverage gives agents flexibility to compose operations. When uncertain, prioritize comprehensive API coverage.

**Tool Naming and Discoverability:**
Clear, descriptive tool names help agents find the right tools quickly. Use consistent prefixes and action-oriented naming.

**Context Management:**
Agents benefit from concise tool descriptions and the ability to filter/paginate results. Design tools that return focused, relevant data.

**Actionable Error Messages:**
Error messages should guide agents toward solutions with specific suggestions and next steps.

#### 1.2 Study MCP Protocol Documentation

Start with the sitemap: `https://modelcontextprotocol.io/sitemap.xml`
Then fetch specific pages with `.md` suffix.

Key pages to review:
- Specification overview and architecture
- Transport mechanisms (streamable HTTP, stdio)
- Tool, resource, and prompt definitions

#### 1.3 Study Framework Documentation

**Recommended stack:** TypeScript with stdio for local servers.

**Reference docs (saved locally):**
- [MCP Best Practices](./reference/mcp_best_practices.md)
- [TypeScript Guide](./reference/node_mcp_server.md)
- [Evaluation Guide](./reference/evaluation.md)

#### 1.4 Plan Your Implementation

Review the service's API documentation. Use web search and WebFetch as needed. List endpoints to implement, starting with the most common operations.

---

### Phase 2: Implementation

#### 2.1 Set Up Project Structure
See TypeScript Guide for project setup.

#### 2.2 Implement Core Infrastructure
- API client with authentication
- Error handling helpers
- Response formatting
- Pagination support

#### 2.3 Implement Tools

For each tool:
- **Input Schema:** Use Zod with constraints and clear descriptions
- **Output Schema:** Define `outputSchema` where possible
- **Tool Description:** Concise summary, parameter descriptions, return type
- **Implementation:** Async/await, proper error handling, pagination
- **Annotations:** readOnlyHint, destructiveHint, idempotentHint, openWorldHint

---

### Phase 3: Review and Test

- No duplicated code (DRY)
- Consistent error handling
- Full type coverage
- Clear tool descriptions
- Run `npm run build` to verify compilation
- Test with MCP Inspector: `npx @modelcontextprotocol/inspector`

---

### Phase 4: Create Evaluations

Create 10 complex, realistic test questions requiring multiple tool calls.
See [Evaluation Guide](./reference/evaluation.md) for complete guidelines.

Requirements:
- Independent, read-only, stable, verifiable
- Single clear answer per question
- XML format output

```xml
<evaluation>
  <qa_pair>
    <question>Your question here</question>
    <answer>Single verifiable answer</answer>
  </qa_pair>
</evaluation>
```
