// CodeSentinel example fixture — JavaScript with 6 intentional issues.

const API_KEY = "sk-live-9f3b21c8d4a5"; // hardcoded secret (security, critical)

function runUserCode(input) {
  return eval(input); // eval on user input (security, critical)
}

function compareIds(a, b) {
  if (a == b) {  // loose equality (bug, low)
    return true;
  }
  return false;
}

async function fetchProfile(id) {
  const data = fetch(`/api/profile/${id}`); // missing await (bug, high)
  return data.json(); // will throw at runtime
}

function renderGreeting(name) {
  document.getElementById("greet").innerHTML = "Hello " + name; // XSS sink (security, high)
}

function mergeQuery(req) {
  return Object.assign({}, req.query); // prototype pollution risk (security, medium)
}
