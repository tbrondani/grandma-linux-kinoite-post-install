# Offline sentence translation

Open **Utilities → Translator**. Select two languages, type or paste a short text, then select **Translate**. Internet is not needed after setup.

The app uses Argos Translate 1.11.0 and its upstream GUI 1.6.5, with a small English/PT-BR interface adapter. Ten pinned models cover Portuguese ↔ English, Spanish, French, German and Italian. French, German and Italian use English as an intermediate language. Portuguese models are not specific to Brazil and can produce European vocabulary. Translation quality needs human review.

Argos has no confirmed official Flatpak for this integration. Setup installs a dedicated Python 3.12 environment in the user's home directory. It does not change system Python. Packages and model downloads are pinned with hashes. MiniSBD sentence models are installed in advance; typing does not trigger translation or model downloads. No speech models, GPU packages or background service are installed.

In the development VM (four virtual CPUs, Intel Core Ultra 7 165H host, 8 GB RAM), ten translation directions passed with the network isolated. GUI translation used about 527 MiB peak RSS. A sequence through all directions used about 1,522 MiB. First non-cached example translations took about 0.15–0.49 seconds after import. Repeated identical inputs are cached and are not a speed benchmark. The seventh-generation i5 still needs a hardware test.

See [installation sizes](INSTALLATION-SIZE.md).
