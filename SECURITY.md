# Security policy

Report suspected vulnerabilities privately through the contact details on [Jarjish Siddibapa's portfolio](https://jarjishsiddibapa.github.io/jarjish-portfolio-website/). Do not attach real PDFs, certificate files, token details, PINs, user databases, or signed outputs to public issues.

## Repository safeguards

The ignore policy blocks documents, databases, certificate/key formats, build folders, installers, and generated outputs. Before publishing a release, review `git ls-files`, inspect the staged diff, and run a secret scan. Use only synthetic documents in tests and documentation.

## Deployment

Set a unique `RDC_SIGNATURES_ADMIN_PASSWORD` at runtime if master-administrator access is required. Do not bake it into a launcher, spec file, installer, screenshot, or support document. Keep PKCS#11 middleware current and distribute installers through an authenticated internal channel.
