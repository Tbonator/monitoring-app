"""
Contract test for integrations/django/example_settings.py.

The snippet is appended to an application's settings.py, so it runs against
names (INSTALLED_APPS, MIDDLEWARE, ALLOWED_HOSTS) that it does not define. This
test executes it against representative base settings and checks the promises
it makes: additions only, nothing overwritten, django-prometheus wrapping ALL
other middleware (wrong ordering silently skews request/latency metrics),
list or tuple settings accepted, and safe to apply more than once.

No Django install needed. Run: python -I tests\\test_example_settings.py
"""
import copy
import sys
from pathlib import Path

SNIPPET = Path(__file__).resolve().parent.parent / "integrations" / "django" / "example_settings.py"
SOURCE = SNIPPET.read_text(encoding="utf-8-sig")  # file carries a UTF-8 BOM
CODE = compile(SOURCE, str(SNIPPET), "exec")
BEFORE = "django_prometheus.middleware.PrometheusBeforeMiddleware"
AFTER = "django_prometheus.middleware.PrometheusAfterMiddleware"
EXTRA_HOSTS = ["localhost", "127.0.0.1", "[::1]", "host.docker.internal"]
CHANGED = {"INSTALLED_APPS", "MIDDLEWARE", "ALLOWED_HOSTS"}

APPS = ["django.contrib.admin", "django.contrib.auth", "arrangements"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
HOSTS = ["backoffice.example.test"]
BASE = {
    "DEBUG": False,
    "SECRET_KEY": "fake-test-only",
    "INSTALLED_APPS": APPS,
    "MIDDLEWARE": MIDDLEWARE,
    "ALLOWED_HOSTS": HOSTS,
    "ROOT_URLCONF": "project.urls",
}

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def apply_snippet(ns, times=1):
    """Run the snippet in a settings namespace; return its setting names only.

    Django treats only UPPERCASE module attributes as settings, so dunders
    (__builtins__, __doc__) are dropped and lowercase/underscore helpers are
    reported so check_contract can flag any that leak.
    """
    ns = copy.deepcopy(ns)
    for _ in range(times):
        exec(CODE, ns)
    return {k: v for k, v in ns.items() if not k.startswith("__")}


def check_contract(label, base, times=1):
    try:
        result = apply_snippet(base, times)
    except Exception as exc:  # e.g. TypeError on tuple settings
        failures.append(f"[{label}] snippet raised {type(exc).__name__}: {exc}")
        return

    # 1. Middleware: Before first, After last, originals intact and in order.
    mw = result["MIDDLEWARE"]
    check(mw == [BEFORE] + MIDDLEWARE + [AFTER], f"[{label}] unexpected MIDDLEWARE: {mw}")

    # 2. INSTALLED_APPS / ALLOWED_HOSTS: appended once, existing entries preserved.
    check(result["INSTALLED_APPS"] == APPS + ["django_prometheus"],
          f"[{label}] unexpected INSTALLED_APPS: {result['INSTALLED_APPS']}")
    check(result["ALLOWED_HOSTS"] == HOSTS + EXTRA_HOSTS,
          f"[{label}] unexpected ALLOWED_HOSTS: {result['ALLOWED_HOSTS']}")
    for key in CHANGED:
        check(isinstance(result[key], list), f"[{label}] {key} is not a list")

    # 3. Additions only: no other setting or helper created, removed or changed.
    check(set(result) == set(base), f"[{label}] snippet created/removed names: {set(result) ^ set(base)}")
    for key in set(base) - CHANGED:
        check(result.get(key) == base[key], f"[{label}] snippet overwrote {key}")

    # 4. No wildcard host: the snippet must never widen ALLOWED_HOSTS to "*".
    check("*" not in result["ALLOWED_HOSTS"], f"[{label}] snippet added wildcard ALLOWED_HOSTS")


check_contract("list settings", BASE)
check_contract("tuple settings", {**BASE, **{k: tuple(BASE[k]) for k in CHANGED}})
check_contract("applied twice", BASE, times=2)
check_contract("applied three times, tuples", {**BASE, **{k: tuple(BASE[k]) for k in CHANGED}}, times=3)
check_contract("already has misplaced prometheus middleware", {
    **BASE,
    "INSTALLED_APPS": APPS + ["django_prometheus"],
    "MIDDLEWARE": [MIDDLEWARE[0], AFTER, *MIDDLEWARE[1:], BEFORE],
    "ALLOWED_HOSTS": HOSTS + ["localhost"],
})

# 5. The snippet must not wire the unauthenticated django_prometheus URLconf.
code_lines = [ln for ln in SOURCE.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
check(not any("django_prometheus.urls" in ln for ln in code_lines),
      "snippet includes django_prometheus.urls (exposes /metrics without auth)")

if failures:
    print("FAIL:", *failures, sep="\n  ")
    sys.exit(1)
print("PASS: example_settings.py only appends, wraps all middleware, "
      "accepts lists or tuples, and is safe to apply repeatedly (5 scenarios)")
