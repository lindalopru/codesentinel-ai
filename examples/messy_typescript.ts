// CodeSentinel example fixture — TypeScript with 5 intentional issues.

import { readFileSync } from "fs"; // unused import (style)

function add(a: any, b: any) {  // any types + missing return type (style, medium)
  return a + b;
}

function divide(x: number, y: number) {
  // @ts-ignore — silences a real bug (bug, medium)
  return x / y.value;
}

async function loadUser(id: string) {
  console.log("loading", id); // console.log left in (style, low)
  const data = await fetch("/u/" + id);
  return data.json();
}

export function unsafeParse(raw: string) {
  return JSON.parse(raw); // no error handling on parse (bug, medium)
}
