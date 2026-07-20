// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Giancarlo Erra - Altaire Limited

import { Lang } from "@ast-grep/napi";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { ensureDynamicLanguages } from "../../src/services/code-graph.js";
import {
  extractSymbolsAndCalls,
  rawCallsToUnresolvedEdges,
  resetSymbolExtractionWarnings,
} from "../../src/services/graph-symbols.js";
import { logger } from "../../src/services/logger.js";

beforeAll(() => {
  ensureDynamicLanguages();
});

describe("graph-symbols", () => {
  describe("TypeScript/JavaScript", () => {
    it("extracts function declarations and synthesizes a <module> symbol", () => {
      const src = `
function foo() { return 1; }
function bar() { return foo(); }
`;
      const out = extractSymbolsAndCalls(src, Lang.TypeScript, ".ts", "src/a.ts");
      const names = out.symbols.map((s) => s.name).sort();
      expect(names).toContain("<module>");
      expect(names).toContain("foo");
      expect(names).toContain("bar");
    });

    it("attributes calls inside a function to that function as caller", () => {
      const src = `
function foo() {}
function bar() { foo(); }
`;
      const out = extractSymbolsAndCalls(src, Lang.TypeScript, ".ts", "src/b.ts");
      const fooCall = out.rawCalls.find((c) => c.calleeName === "foo");
      expect(fooCall).toBeDefined();
      expect(fooCall?.callerId).toContain("::bar#");
    });

    it("extracts class methods with qualified names", () => {
      const src = `
class Foo {
  bar() { return 1; }
  baz() { return this.bar(); }
}
`;
      const out = extractSymbolsAndCalls(src, Lang.TypeScript, ".ts", "src/c.ts");
      const qnames = out.symbols.map((s) => s.qualifiedName);
      expect(qnames).toContain("Foo.bar");
      expect(qnames).toContain("Foo.baz");
      const kinds = out.symbols.filter((s) => s.qualifiedName === "Foo.bar").map((s) => s.kind);
      expect(kinds).toContain("method");
    });

    it("extracts arrow function constants", () => {
      const src = `
export const validate = (x: number) => x > 0;
const helper = function () { return 42; };
`;
      const out = extractSymbolsAndCalls(src, Lang.TypeScript, ".ts", "src/d.ts");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("validate");
      expect(names).toContain("helper");
    });
  });

  describe("Python", () => {
    it("extracts def and class symbols", () => {
      const src = `
def foo():
    return 1

class Bar:
    def baz(self):
        return foo()
`;
      const out = extractSymbolsAndCalls(src, "python" as unknown as Lang, ".py", "app.py");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("foo");
      expect(names).toContain("Bar");
      expect(names).toContain("baz");
    });
  });

  describe("Go", () => {
    it("extracts func declarations", () => {
      const src = `
package main

func Foo() int { return 1 }

func Bar() int { return Foo() }
`;
      const out = extractSymbolsAndCalls(src, "go" as unknown as Lang, ".go", "main.go");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("Foo");
      expect(names).toContain("Bar");
    });
  });

  describe("rawCallsToUnresolvedEdges", () => {
    it("converts raw calls to unresolved SymbolEdge objects", () => {
      const raw = [
        {
          callerId: "src/a.ts::foo#1",
          calleeName: "bar",
          callSite: { file: "src/a.ts", line: 5 },
        },
      ];
      const edges = rawCallsToUnresolvedEdges(raw);
      expect(edges).toHaveLength(1);
      expect(edges[0].confidence).toBe("unresolved");
      expect(edges[0].calleeCandidates).toEqual([]);
      expect(edges[0].calleeName).toBe("bar");
    });
  });

  describe("Rust", () => {
    it("extracts fn and impl methods", () => {
      const src = `
fn foo() -> i32 { 1 }

struct S;
impl S {
    fn bar(&self) -> i32 { foo() }
}
`;
      const out = extractSymbolsAndCalls(src, "rust" as unknown as Lang, ".rs", "lib.rs");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("foo");
      expect(names).toContain("bar");
      expect(out.symbols.some((s) => s.name === "<module>")).toBe(true);
    });
  });

  describe("Java / Kotlin / Scala (JVM family)", () => {
    it("extracts Java class and methods", () => {
      const src = `
public class Foo {
    public int bar() { return 1; }
    public int baz() { return bar(); }
}
`;
      const out = extractSymbolsAndCalls(src, "java" as unknown as Lang, ".java", "Foo.java");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("Foo");
      expect(names).toContain("bar");
      expect(names).toContain("baz");
    });

    it("prefers the declared Java class name over parameter types in Spring Boot entrypoints", () => {
      const src = `
@SpringBootApplication
public class WorkflowFlowableApplication {
    public static void main(String[] args) {
        SpringApplication.run(WorkflowFlowableApplication.class, args);
    }
}
`;
      const out = extractSymbolsAndCalls(src, "java" as unknown as Lang, ".java", "WorkflowFlowableApplication.java");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("WorkflowFlowableApplication");
      expect(names).not.toContain("String");
      expect(names).toContain("main");
    });

    it("does not treat Java test annotations as method names", () => {
      const src = `
class SecurityAuthClientRequireSubjectTest {
    @AfterEach
    void cleanup() {}

    @Test
    void requireSubjectThrows() {}

    @Test(timeout = 1000)
    void fastTest() {}
}
`;
      const out = extractSymbolsAndCalls(src, "java" as unknown as Lang, ".java", "SecurityAuthClientRequireSubjectTest.java");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("SecurityAuthClientRequireSubjectTest");
      expect(names).toContain("cleanup");
      expect(names).toContain("requireSubjectThrows");
      expect(names).toContain("fastTest");
      expect(names).not.toContain("AfterEach");
      expect(names).not.toContain("Test");
    });

    it("preserves Java declarations when annotations share the same line", () => {
      const src = `
class InlineAnnotationTest {
    @Test void cleanup() {}
}
`;
      const out = extractSymbolsAndCalls(src, "java" as unknown as Lang, ".java", "InlineAnnotationTest.java");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("InlineAnnotationTest");
      expect(names).toContain("cleanup");
      expect(names).not.toContain("Test");
    });

    it("extracts Kotlin top-level fun and class methods", () => {
      const src = `
fun greet(name: String): String = "Hi"

class Bar {
    fun work(): String = greet("x")
}
`;
      const out = extractSymbolsAndCalls(src, "kotlin" as unknown as Lang, ".kt", "main.kt");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("greet");
      expect(names).toContain("Bar");
      expect(names).toContain("work");
    });

    it("extracts Scala def and class", () => {
      const src = `
class Foo {
  def bar(): Int = 1
  def size: Int = 1
  def now = Instant.now()
}

object Main {
  def main(args: Array[String]): Unit = println("hi")
}
`;
      const out = extractSymbolsAndCalls(src, "scala" as unknown as Lang, ".scala", "Main.scala");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("bar");
      expect(names).toContain("size");
      expect(names).toContain("now");
      expect(names).toContain("main");
    });
  });

  describe("C#", () => {
    it("extracts class and methods", () => {
      const src = `
namespace App {
    public class Foo {
        public int Bar() { return 1; }
        public int Baz() { return Bar(); }
    }
}
`;
      const out = extractSymbolsAndCalls(src, "csharp" as unknown as Lang, ".cs", "Foo.cs");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("Foo");
      expect(names).toContain("Bar");
      expect(names).toContain("Baz");
    });
  });

  describe("C / C++", () => {
    it("extracts C function definitions", () => {
      const src = `
int add(int a, int b) { return a + b; }

int main(void) {
    return add(2, 3);
}
`;
      const out = extractSymbolsAndCalls(src, "c" as unknown as Lang, ".c", "main.c");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("add");
      expect(names).toContain("main");
    });

    it("extracts C++ class declarations and free functions", () => {
      // Note: inline class methods are `field_declaration` nodes in tree-sitter-cpp,
      // not `function_definition`, so the current extractor catches them only
      // when defined out-of-line. See language-coverage table in DEVELOPER.md.
      const src = `
class Foo {
public:
    int bar();
};

int Foo::bar() { return 1; }
int helper() { return 42; }
`;
      const out = extractSymbolsAndCalls(src, "cpp" as unknown as Lang, ".cpp", "Foo.cpp");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("Foo");
      expect(names).toContain("helper");
      // Out-of-line method `Foo::bar` is detected as qualifiedName "Foo::bar".
      const qnames = out.symbols.map((s) => s.qualifiedName);
      expect(qnames.some((q) => q === "Foo::bar" || q === "bar")).toBe(true);
    });
  });

  describe("Ruby", () => {
    it("extracts def and class", () => {
      const src = `
def foo
  1
end

class Bar
  def baz
    foo
  end
end
`;
      const out = extractSymbolsAndCalls(src, "ruby" as unknown as Lang, ".rb", "app.rb");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("foo");
      expect(names).toContain("Bar");
      expect(names).toContain("baz");
    });
  });

  describe("PHP", () => {
    it("extracts function and class methods", () => {
      const src = `<?php
function greet($name) {
  return "Hi " . $name;
}

class Foo {
  public function bar() {
    return greet("x");
  }
}
`;
      const out = extractSymbolsAndCalls(src, "php" as unknown as Lang, ".php", "index.php");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("greet");
      expect(names).toContain("Foo");
      expect(names).toContain("bar");
    });
  });

  describe("Swift", () => {
    it("extracts Swift func and class", () => {
      const src = `
func greet(name: String) -> String { return "Hi" }

class Foo {
    func bar() -> String { return greet(name: "x") }
}
`;
      const out = extractSymbolsAndCalls(src, "swift" as unknown as Lang, ".swift", "App.swift");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("greet");
      expect(names).toContain("Foo");
      expect(names).toContain("bar");
    });
  });

  describe("Bash", () => {
    it("extracts shell function definitions", () => {
      const src = `
greet() {
  echo "hi $1"
}

main() {
  greet "world"
}
`;
      const out = extractSymbolsAndCalls(src, "bash" as unknown as Lang, ".sh", "run.sh");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("greet");
      expect(names).toContain("main");
    });
  });

  describe("Lua", () => {
    it("extracts namespace-table, method, local, and assignment function forms", () => {
      const src = `
local T = {}

function T.method(a)
  return a
end

function T:m()
  return self
end

local function helper()
  return 1
end

T.f = function()
  return 2
end

return T
`;
      const out = extractSymbolsAndCalls(src, "lua" as unknown as Lang, ".lua", "init.lua");
      const names = out.symbols.map((s) => s.name);
      const qnames = out.symbols.map((s) => s.qualifiedName);
      expect(names).toContain("<module>");
      // qualified Table.method / T:m() forms resolve to precise method symbols
      expect(qnames).toContain("T.method");
      expect(qnames).toContain("T:m");
      // `local function` keeps its bare name
      expect(names).toContain("helper");
      // `T.f = function() … end` assignment form
      expect(qnames).toContain("T.f");
      const kinds = out.symbols.filter((s) => s.qualifiedName === "T.method").map((s) => s.kind);
      expect(kinds).toContain("method");
      // colon-call form is also a method; the plain local function is not
      expect(out.symbols.find((s) => s.qualifiedName === "T:m")?.kind).toBe("method");
      expect(out.symbols.find((s) => s.qualifiedName === "helper")?.kind).toBe("function");
    });

    it("attributes calls to the enclosing function", () => {
      const src = `
function greet(name)
  return "hi " .. name
end

local function helper()
  return greet("x")
end
`;
      const out = extractSymbolsAndCalls(src, "lua" as unknown as Lang, ".lua", "init.lua");
      expect(out.symbols.some((s) => s.name === "<module>")).toBe(true);
      const greetCall = out.rawCalls.find((c) => c.calleeName === "greet");
      expect(greetCall).toBeDefined();
      expect(greetCall?.callerId).toContain("::helper#");
    });

    it("extracts the `local f = function() … end` assignment form", () => {
      const src = `
local f = function()
  return 1
end

local g = function()
  return f()
end
`;
      const out = extractSymbolsAndCalls(src, "lua" as unknown as Lang, ".lua", "init.lua");
      const names = out.symbols.map((s) => s.name);
      expect(names).toContain("f");
      expect(names).toContain("g");
      expect(out.symbols.find((s) => s.qualifiedName === "f")?.kind).toBe("function");
      // call to `f` lives inside `g`, so it is attributed to `g`
      const fCall = out.rawCalls.find((c) => c.calleeName === "f");
      expect(fCall?.callerId).toContain("::g#");
    });

    it("attributes top-level calls to <module> and resolves dotted callees", () => {
      const src = `
local M = require("mod")

M.setup()

local function run()
  M.start()
end
`;
      const out = extractSymbolsAndCalls(src, "lua" as unknown as Lang, ".lua", "init.lua");
      // calls outside any function fall back to the synthetic <module> scope
      const requireCall = out.rawCalls.find((c) => c.calleeName === "require");
      expect(requireCall?.callerId).toContain("::<module>#");
      // dotted callee `M.setup` resolves to the trailing identifier
      const setupCall = out.rawCalls.find((c) => c.calleeName === "setup");
      expect(setupCall).toBeDefined();
      expect(setupCall?.callerId).toContain("::<module>#");
      // `M.start()` lives inside `run`, so it is attributed there
      const startCall = out.rawCalls.find((c) => c.calleeName === "start");
      expect(startCall?.callerId).toContain("::run#");
    });
  });

  describe("Dart", () => {
    it("extracts type-first declarations the regex fallback could never match", () => {
      const src = `
class Foo {
  Foo(int c);
  Foo.named(int c);
  factory Foo.create() => Foo(1);
  void bar(int x) {
    helper(x);
  }
  String get name => 'foo';
  set name(String v) {}
}

mixin Loggable {
  void log(String msg) {}
}

enum Color { red, green }

extension StrExt on String {
  int len() => length;
}

typedef Callback = void Function(int);

Future<int> fetchCount() async {
  return 1;
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/foo.dart");
      const has = (qn: string, kind: string) =>
        out.symbols.some((s) => s.qualifiedName === qn && s.kind === kind);

      expect(has("Foo", "class")).toBe(true);
      // Constructors: plain, named, and factory all resolve as constructors
      // with dotted qualified names — the regex fallback saw none of these.
      // The plain constructor deliberately shares the class's qualified name
      // (that is how call sites reference it); they differ by kind and line.
      expect(has("Foo", "constructor")).toBe(true);
      expect(has("Foo.named", "constructor")).toBe(true);
      expect(has("Foo.create", "constructor")).toBe(true);
      expect(has("Foo.bar", "method")).toBe(true);
      // Getter and setter share a name but live on different lines (distinct ids)
      const nameSyms = out.symbols.filter((s) => s.qualifiedName === "Foo.name");
      expect(nameSyms).toHaveLength(2);
      expect(has("Loggable", "trait")).toBe(true);
      expect(has("Loggable.log", "method")).toBe(true);
      expect(has("Color", "enum")).toBe(true);
      expect(has("StrExt.len", "method")).toBe(true);
      expect(has("Callback", "interface")).toBe(true);
      // Type-first top-level signature (`Future<int> fetchCount()`)
      expect(has("fetchCount", "function")).toBe(true);
    });

    it("stitches a top-level function's scope from its sibling signature and body", () => {
      const src = `
void helper(int x) {
  print(x);
  print(x + 1);
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/h.dart");
      const helper = out.symbols.find((s) => s.qualifiedName === "helper");
      // The signature node alone ends on line 2; the scope must reach the
      // body's closing brace, otherwise calls inside attribute to <module>.
      expect(helper?.line).toBe(2);
      expect(helper?.endLine).toBe(5);
      const printCall = out.rawCalls.find((c) => c.calleeName === "print");
      expect(printCall?.callerId).toContain("::helper#");
    });

    it("attributes method calls, cascades, and constructor invocations to the enclosing scope", () => {
      const src = `
class Foo {
  void bar(int x) {}
  Future<void> load() async {}
}

void main() {
  final f = Foo(1);
  f.bar(2);
  f..bar(3)..load();
  mat.runApp();
  helper(5);
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/main.dart");
      const fromMain = out.rawCalls.filter((c) => c.callerId.includes("::main#"));
      const callees = fromMain.map((c) => c.calleeName);

      // Constructor invocation (`Foo(1)`, no `new` keyword in modern Dart)
      expect(callees).toContain("Foo");
      // Plain method call `f.bar(2)`
      expect(callees).toContain("bar");
      // Cascade `..load()` — a Dart-only form with its own grammar shape
      expect(callees).toContain("load");
      // Prefixed call `mat.runApp()` resolves to the trailing identifier
      expect(callees).toContain("runApp");
      // Bare call
      expect(callees).toContain("helper");
    });

    it("degrades gracefully on Dart 3.3 extension types (unsupported by grammar 0.0.7)", () => {
      // The vendored tree-sitter grammar predates `extension type` and parses
      // it to ERROR nodes. The contract: no throw, no bogus symbols from the
      // ERROR region, and the rest of the file still extracts normally.
      const src = `
extension type Meters(int value) {
  int get inKm => value ~/ 1000;
}

class Real {
  void work() {}
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/m.dart");
      expect(out.symbols.some((s) => s.qualifiedName === "Real" && s.kind === "class")).toBe(true);
      expect(out.symbols.some((s) => s.qualifiedName === "Real.work" && s.kind === "method")).toBe(true);
      // The unsupported declaration produces no symbol named Meters
      expect(out.symbols.some((s) => s.name === "Meters")).toBe(false);
    });

    it("detects main() so Dart apps get a conventional entry point", () => {
      const src = `
void main() {
  runApp();
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "bin/app.dart");
      const main = out.symbols.find((s) => s.name === "main");
      expect(main).toBeDefined();
      expect(main?.kind).toBe("function");
    });

    it("extracts abstract bodyless getters, setters, and methods (#74)", () => {
      // Bodyless members parse as `declaration > <signature>` (no function_body),
      // which the original extractor skipped. They are common in Dart interfaces
      // and abstract classes.
      const src = `
abstract class Repo {
  Future<int> load();
  int get count;
  set name(String v);
  void clear() {}
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/repo.dart");
      const has = (qn: string, kind: string) =>
        out.symbols.some((s) => s.qualifiedName === qn && s.kind === kind);
      expect(has("Repo", "class")).toBe(true);
      expect(has("Repo.load", "method")).toBe(true); // abstract method
      expect(has("Repo.count", "method")).toBe(true); // abstract getter
      expect(has("Repo.name", "method")).toBe(true); // abstract setter
      expect(has("Repo.clear", "method")).toBe(true); // concrete method still works
    });

    it("extracts operators (with and without a body), named by their token (#74)", () => {
      // Operators are not named by an identifier; the symbol is `operator<token>`.
      const src = `
class Vec {
  Vec operator +(Vec o) => o;
  bool operator ==(Object o) => true;
  num operator [](int i) => i;
  Vec operator -(Vec o);
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/vec.dart");
      const qns = out.symbols.map((s) => s.qualifiedName);
      expect(qns).toContain("Vec.operator+"); // binary, with body
      expect(qns).toContain("Vec.operator=="); // equality, with body
      expect(qns).toContain("Vec.operator[]"); // index, with body
      expect(qns).toContain("Vec.operator-"); // abstract (bodyless) operator
      for (const s of out.symbols) {
        if (s.qualifiedName.startsWith("Vec.operator")) expect(s.kind).toBe("method");
      }
    });

    it("does not regress fields, constructors, or getters-with-body (#74)", () => {
      // The new abstract-member handling must not change anything that already
      // worked, and must keep skipping plain fields.
      const src = `
class Foo {
  int count = 0;
  Foo(this.count);
  factory Foo.create() => Foo(0);
  String get label => "x";
}
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/foo.dart");
      const has = (qn: string, kind: string) =>
        out.symbols.some((s) => s.qualifiedName === qn && s.kind === kind);
      expect(has("Foo", "class")).toBe(true);
      expect(has("Foo.create", "constructor")).toBe(true);
      expect(has("Foo.label", "method")).toBe(true); // getter with body
      // Field `count` is not callable and must NOT become a symbol.
      expect(out.symbols.some((s) => s.qualifiedName === "Foo.count")).toBe(false);
    });

    it("recovers sibling classes when an unparseable sealed class is present (#74)", () => {
      // sealed class is Dart 3 syntax the grammar cannot parse. It is lost, but
      // the regular classes and enums around it must still be extracted, not
      // zeroed out. This pins the partial-degradation behavior.
      const src = `
class Before { void a() {} }

sealed class Sealed { int get id; }

class After { void b() {} }

enum Color { red, green }
`;
      const out = extractSymbolsAndCalls(src, "dart" as unknown as Lang, ".dart", "lib/mixed.dart");
      expect(out.symbols.some((s) => s.qualifiedName === "Before" && s.kind === "class")).toBe(true);
      expect(out.symbols.some((s) => s.qualifiedName === "Before.a" && s.kind === "method")).toBe(true);
      expect(out.symbols.some((s) => s.qualifiedName === "After" && s.kind === "class")).toBe(true);
      expect(out.symbols.some((s) => s.qualifiedName === "After.b" && s.kind === "method")).toBe(true);
      expect(out.symbols.some((s) => s.qualifiedName === "Color" && s.kind === "enum")).toBe(true);
      // The sealed class itself cannot be parsed by this grammar version.
      expect(out.symbols.some((s) => s.qualifiedName === "Sealed")).toBe(false);
    });

    it("warns once (not per file) when Dart files contain unparseable syntax (#74)", () => {
      resetSymbolExtractionWarnings();
      const warnSpy = vi.spyOn(logger, "warn").mockImplementation(() => undefined);
      try {
        const sealed = "sealed class A { int get id; }\n";
        extractSymbolsAndCalls(sealed, "dart" as unknown as Lang, ".dart", "lib/a.dart");
        extractSymbolsAndCalls(sealed, "dart" as unknown as Lang, ".dart", "lib/b.dart");
        const dartWarns = warnSpy.mock.calls.filter(([msg]) =>
          typeof msg === "string" && msg.includes("@ast-grep/lang-dart"),
        );
        // Two files with errors, but the process-level dedup emits exactly one warn.
        expect(dartWarns).toHaveLength(1);
      } finally {
        warnSpy.mockRestore();
        resetSymbolExtractionWarnings();
      }
    });
  });

  describe("Regex fallback (Svelte, Vue, unknown)", () => {
    it("handles unknown language without throwing", () => {
      const src = "some random text\nwith no recognizable structure";
      const out = extractSymbolsAndCalls(
        src,
        "unknown" as unknown as Lang,
        ".xyz",
        "data.xyz",
      );
      expect(out.symbols.some((s) => s.name === "<module>")).toBe(true);
      expect(out.rawCalls).toEqual([]);
    });
  });
});
