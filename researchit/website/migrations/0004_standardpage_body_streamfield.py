"""StandardPage.body: rich text -> StreamField (text + table blocks).

Existing text is kept: it becomes one "text" block, on the page and in every saved
revision (drafts included), so the editor and old revisions keep working. The old
column is renamed first because Postgres can't cast HTML to jsonb in place.
"""

import json
import uuid

import wagtail.fields
from django.db import migrations

BODY_BLOCKS = [("text", 0), ("table", 3)]
BLOCK_LOOKUP = {
    0: (
        "wagtail.blocks.RichTextBlock",
        (),
        {"features": ["h2", "h3", "bold", "italic", "link", "ol", "ul", "hr", "document-link"]},
    ),
    1: ("wagtail.blocks.CharBlock", (), {}),
    2: ("wagtail.blocks.RichTextBlock", (), {"features": ["bold", "italic", "link"]}),
    3: (
        "wagtail.contrib.typed_table_block.blocks.TypedTableBlock",
        [[("text", 1), ("rich_text", 2)]],
        {"template": "website/blocks/table.html"},
    ),
}


def _text_block(html):
    return [{"type": "text", "value": html, "id": str(uuid.uuid4())}]


def _revisions(apps, schema_editor):
    content_type = apps.get_model("contenttypes", "ContentType").objects.filter(
        app_label="researchit_website", model="standardpage"
    )
    revision = apps.get_model("wagtailcore", "Revision")
    return revision.objects.using(schema_editor.connection.alias).filter(content_type__in=content_type)


def forwards(apps, schema_editor):
    db = schema_editor.connection.alias
    page_model = apps.get_model("researchit_website", "StandardPage")
    for page in page_model.objects.using(db).exclude(body_html=""):
        page.body = json.dumps(_text_block(page.body_html))
        page.save(update_fields=["body"])

    for rev in _revisions(apps, schema_editor):
        body = rev.content.get("body")
        if not isinstance(body, str):
            continue
        try:
            json.loads(body)  # already StreamField JSON
        except ValueError:
            rev.content["body"] = json.dumps(_text_block(body) if body else [])
            rev.save(update_fields=["content"])


def backwards(apps, schema_editor):
    """Flatten text blocks back to HTML (tables are dropped)."""

    def flatten(stream):
        return "".join(b["value"] for b in stream if b.get("type") == "text")

    db = schema_editor.connection.alias
    page_model = apps.get_model("researchit_website", "StandardPage")
    for page in page_model.objects.using(db).all():
        page.body_html = flatten(page.body.raw_data) if page.body else ""
        page.save(update_fields=["body_html"])

    for rev in _revisions(apps, schema_editor):
        body = rev.content.get("body")
        if isinstance(body, str):
            try:
                rev.content["body"] = flatten(json.loads(body))
            except ValueError:
                continue
            rev.save(update_fields=["content"])


class Migration(migrations.Migration):
    dependencies = [
        ("researchit_website", "0003_business_owner_and_seo"),
        ("wagtailcore", "0098_apitoken"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RenameField(model_name="standardpage", old_name="body", new_name="body_html"),
        migrations.AddField(
            model_name="standardpage",
            name="body",
            field=wagtail.fields.StreamField(BODY_BLOCKS, blank=True, block_lookup=BLOCK_LOOKUP),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="standardpage", name="body_html"),
    ]
