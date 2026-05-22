/**
 * Enforce JSDoc on all exported declarations in `src/`.
 *
 * Uses the TypeScript Compiler API directly (zero extra dependencies).
 * Walks the AST of every `.ts` file and flags exported functions, classes,
 * interfaces, type aliases, enums, and variables that lack a preceding JSDoc
 * comment. Exits non-zero if any violations are found.
 */

import ts from "typescript";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(__dirname, "../src");

const EXPORT_KINDS = new Set([
  ts.SyntaxKind.FunctionDeclaration,
  ts.SyntaxKind.ClassDeclaration,
  ts.SyntaxKind.InterfaceDeclaration,
  ts.SyntaxKind.TypeAliasDeclaration,
  ts.SyntaxKind.EnumDeclaration,
]);

function hasJSDoc(node) {
  return (node.jsDoc && node.jsDoc.length > 0)
    || (ts.getJSDocTags(node) && ts.getJSDocTags(node).length > 0);
}

function isExported(node) {
  return node.modifiers?.some(
    (m) => m.kind === ts.SyntaxKind.ExportKeyword || m.kind === ts.SyntaxKind.DefaultKeyword
  );
}

function collectViolations(sourceFile) {
  const violations = [];

  function visit(node) {
    if (EXPORT_KINDS.has(node.kind) && isExported(node)) {
      if (!hasJSDoc(node)) {
        const { line, character } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
        const name = node.name?.text || "(unnamed)";
        violations.push(
          `${sourceFile.fileName}:${line + 1}:${character + 1} - Missing JSDoc for exported ${ts.SyntaxKind[node.kind]} "${name}"`
        );
      }
    }

    if (ts.isVariableStatement(node) && isExported(node)) {
      if (!hasJSDoc(node)) {
        const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
        const names = node.declarationList.declarations
          .map(d => d.name.getText(sourceFile))
          .join(", ");
        violations.push(
          `${sourceFile.fileName}:${line + 1} - Missing JSDoc for exported variable(s) "${names}"`
        );
      }
    }

    ts.forEachChild(node, visit);
  }

  visit(sourceFile);
  return violations;
}

function findTsFiles(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...findTsFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".ts") && !entry.name.endsWith(".d.ts")) {
      files.push(fullPath);
    }
  }
  return files;
}

const files = findTsFiles(srcDir);
let allViolations = [];

for (const file of files) {
  const sourceText = fs.readFileSync(file, "utf8");
  const sourceFile = ts.createSourceFile(file, sourceText, ts.ScriptTarget.Latest, true);
  allViolations.push(...collectViolations(sourceFile));
}

if (allViolations.length > 0) {
  console.error("JSDoc violations:");
  for (const v of allViolations) {
    console.error(`  ${v}`);
  }
  console.error(`\n${allViolations.length} violation(s) found.`);
  process.exit(1);
}

console.log("All exported declarations have JSDoc.");
