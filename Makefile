# Build the OpenAI Platform upload from the committed plugin files.
# The version, the checked files and the packed files all come from HEAD.

VERSION := $(shell git show HEAD:plugin.json | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')
FILES := plugin.json mcp.json .mcp.json .codex-plugin/plugin.json .claude-plugin/plugin.json assets/logo.png LICENSE README.md

.PHONY: zip
zip:
	@test -n "$(VERSION)" || { echo "Could not read version from HEAD:plugin.json"; exit 1; }
	@git diff --quiet HEAD -- $(FILES) || { echo "Commit or stash your changes to the plugin files first."; exit 1; }
	python3 .github/scripts/check_submission.py
	mkdir -p dist
	git archive --format=zip -o dist/wafeq-$(VERSION).zip HEAD $(FILES)
	@echo "Built dist/wafeq-$(VERSION).zip"
