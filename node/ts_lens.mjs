import { Project } from "ts-morph";
import { readFileSync } from "fs";
import { extname } from "path";

const [, , operation, filePath, symbolName] = process.argv;

if (!operation || !filePath) {
  console.log(JSON.stringify({ error: "Usage: ts_lens.mjs <operation> <file> [symbol]" }));
  process.exit(1);
}

function extractScript(content) {
  const match = content.match(/<script(?:\s[^>]*)?>(\s*[\s\S]*?)<\/script>/ms);
  return match ? match[1] : "";
}

function loadSourceFile(project, path) {
  if (extname(path).toLowerCase() === ".svelte") {
    const raw = readFileSync(path, "utf-8");
    return project.createSourceFile("__svelte__.ts", extractScript(raw), { overwrite: true });
  }
  return project.addSourceFileAtPath(path);
}

function firstDoc(node) {
  const docs = typeof node.getJsDocs === "function" ? node.getJsDocs() : [];
  if (!docs.length) return null;
  const text = docs[0].getDescription().trim();
  return text.split("\n")[0].trim() || null;
}

try {
  const project = new Project({ skipAddingFilesFromTsConfig: true });
  const sf = loadSourceFile(project, filePath);

  if (operation === "structure") {
    const lines = [];
    sf.getInterfaces().forEach(i => lines.push(i.getName()));
    sf.getTypeAliases().forEach(t => lines.push(t.getName()));
    sf.getClasses().forEach(c => {
      lines.push(c.getName() ?? "(anonymous)");
      c.getConstructors().forEach(() => lines.push("  constructor"));
      c.getMethods().forEach(m => lines.push(`  ${m.getName()}`));
      c.getProperties().forEach(p => lines.push(`  ${p.getName()}`));
    });
    sf.getFunctions().forEach(f => {
      const name = f.getName();
      if (name) lines.push(name);
    });
    sf.getVariableDeclarations().forEach(v => {
      const init = v.getInitializer();
      if (init && ["ArrowFunction", "FunctionExpression"].includes(init.getKindName())) {
        lines.push(v.getName());
      }
    });
    console.log(JSON.stringify({ result: lines.join("\n") || "(no symbols found)" }));

  } else if (operation === "skeleton") {
    const lines = [];
    sf.getInterfaces().forEach(i => {
      lines.push(`interface ${i.getName()} {`);
      i.getProperties().forEach(p => lines.push(`  ${p.getName()}: ${p.getType().getText()}`));
      lines.push("}");
      lines.push("");
    });
    sf.getClasses().forEach(c => {
      const doc = firstDoc(c);
      lines.push(`class ${c.getName()} {`);
      if (doc) lines.push(`  /** ${doc} */`);
      c.getConstructors().forEach(ctor => {
        const params = ctor.getParameters().map(p => `${p.getName()}: ${p.getType().getText()}`).join(", ");
        lines.push(`  constructor(${params})`);
      });
      c.getMethods().forEach(m => {
        const async_ = m.isAsync() ? "async " : "";
        const params = m.getParameters().map(p => `${p.getName()}: ${p.getType().getText()}`).join(", ");
        const ret = m.getReturnType().getText();
        lines.push(`  ${async_}${m.getName()}(${params}): ${ret}`);
        const d = firstDoc(m);
        if (d) lines.push(`    /** ${d} */`);
      });
      lines.push("}");
      lines.push("");
    });
    sf.getFunctions().forEach(f => {
      const async_ = f.isAsync() ? "async " : "";
      const params = f.getParameters().map(p => `${p.getName()}: ${p.getType().getText()}`).join(", ");
      const ret = f.getReturnType().getText();
      lines.push(`${async_}function ${f.getName()}(${params}): ${ret}`);
      const d = firstDoc(f);
      if (d) lines.push(`  /** ${d} */`);
    });
    console.log(JSON.stringify({ result: lines.join("\n") || "(no symbols found)" }));

  } else if (operation === "body") {
    if (!symbolName) {
      console.log(JSON.stringify({ error: "symbol name required for body" }));
      process.exit(1);
    }
    let found = null;
    sf.getClasses().forEach(c => { if (c.getName() === symbolName) found = c.getText(); });
    sf.getFunctions().forEach(f => { if (f.getName() === symbolName) found = f.getText(); });
    sf.getInterfaces().forEach(i => { if (i.getName() === symbolName) found = i.getText(); });
    sf.getVariableStatements().forEach(vs => {
      vs.getDeclarations().forEach(d => { if (d.getName() === symbolName) found = vs.getText(); });
    });
    console.log(JSON.stringify({ result: found ?? "" }));

  } else if (operation === "imports") {
    const lines = [];
    sf.getImportDeclarations().forEach(imp => lines.push(imp.getText()));
    sf.getVariableStatements().forEach(vs => {
      if (vs.getText().includes("require(")) lines.push(vs.getText());
    });
    console.log(JSON.stringify({ result: lines.join("\n") || "(no imports)" }));

  } else {
    console.log(JSON.stringify({ error: `Unknown operation: ${operation}` }));
  }
} catch (e) {
  console.log(JSON.stringify({ error: e.message }));
}
