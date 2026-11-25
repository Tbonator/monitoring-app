"""
Idempotent GlitchTip bootstrap (run inside the glitchtip container).
(Do not pipe it via PowerShell 5.1: that adds a BOM and breaks the parse.)

    docker cp scripts\glitchtip-bootstrap.py glitchtip:/tmp/gb.py
    docker exec -e GT_ADMIN_EMAIL=... -e GT_ADMIN_PASSWORD=... -e GT_PROJECT=funeral-back-office `
      glitchtip python manage.py shell --no-imports -c "exec(open('/tmp/gb.py', encoding='utf-8-sig').read())"
    docker exec -u 0 glitchtip rm -f /tmp/gb.py

Save the printed DSN (line "DSN=...") to secrets\<project>-glitchtip.dsn.

Creates (if missing): superuser, organization "Application Monitoring",
project GT_PROJECT with IP scrubbing enabled. Prints the project's DSN on a
line starting with "DSN=" so the caller can store it in secrets/.
"""
import os

from apps.organizations_ext.models import Organization, OrganizationUserRole
from apps.projects.models import Project, ProjectKey
from django.contrib.auth import get_user_model

email = os.environ["GT_ADMIN_EMAIL"]
password = os.environ["GT_ADMIN_PASSWORD"]
project_name = os.environ.get("GT_PROJECT", "funeral-back-office")

User = get_user_model()
user = User.objects.filter(email=email).first()
if user is None:
    user = User.objects.create_superuser(email=email, password=password)
    print("created superuser")

org = Organization.objects.filter(slug="application-monitoring").first()
if org is None:
    org = Organization.objects.create(name="Application Monitoring", slug="application-monitoring")
    print("created organization")
if not org.organization_users.filter(user=user).exists():
    org.add_user(user, role=OrganizationUserRole.OWNER)

project = Project.objects.filter(organization=org, slug=project_name).first()
if project is None:
    project = Project.objects.create(
        organization=org, name=project_name, slug=project_name, platform="python-django"
    )
    print("created project")
project.scrub_ip_addresses = True
project.save()

key = ProjectKey.objects.filter(project=project).first() or ProjectKey.objects.create(project=project)
print("DSN=" + key.get_dsn())
