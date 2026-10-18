# Publish a clean public project

1. Keep private run data outside the export. The normal private workspace is ignored `data/`; it is never in the release manifest.
2. Run the tests and `tools/check_public.py`. Review all public files, not just names. Do not add personal content to the manifest to make a failing check green.
3. Generate the allowlisted public ZIP with `tools/package_public.py`. Open its member list and confirm only instructions, code, configuration examples and synthetic fixtures are present.
4. If using an existing Git repository, audit staged/tracked files and reachable history separately. Ignore rules and a clean ZIP do not erase old commits. If history is not independently verified, publish a fresh repository from the reviewed export, not from an old private checkout.
5. Create a repository in your own GitHub account, choose its name and visibility, and commit the reviewed public files. Nothing in this toolkit creates a remote, commits, pushes or changes visibility for you.
6. Confirm the public repository contains no real statements, screenshots, transaction exports, private configuration, personal account names, password candidates or private paths. Test the published download in a new directory with the synthetic demo.

The included MIT license allows reuse; review the license choice before publishing. GitHub Actions checks are supplied but are not verified on a hosted runner until you actually push and run them. Major-version action tags should be reviewed/updated as part of maintenance.

After publication, replace any social-post placeholder with the real repository URL. Do not claim the project is already published, fully hands-free or a universal statement parser. The AI workflow handles extraction/review with human oversight; the local helpers validate normalized data and produce reports.

## Optional social graphic

`docs/assets/workflow.svg` is a source-editable public diagram with no transaction data. To create a PNG, use an environment with Node.js, Playwright and its Chromium browser, then run `node tools/render_social.mjs`. Install optional browser dependencies under ignored `data/` or in an existing development environment, not as unreviewed files in the public source tree. You can point `BUDGET_PLAYWRIGHT_MODULE` at that environment's Playwright module. The renderer writes `dist/workflow-linkedin.png` and refuses to overwrite an existing file. Review the image before uploading; the script never posts it.
