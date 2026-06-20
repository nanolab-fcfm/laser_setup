# User Guide

The User Guide explains how Laser Setup is put together and how each part
behaves. Where the [Tutorials](../tutorials/index.md) teach by doing, these pages
are the reference you come back to.

<div class="grid cards" markdown>

-   :material-sitemap: **[Architecture](architecture.md)**

    The big picture: how the entry point, config, GUI, procedures and
    instruments interact.

-   :material-application: **[The Graphical Interface](gui.md)**

    Main window, experiment window, sequence window and the widgets.

-   :material-cog: **[Configuration System](configuration.md)**

    YAML + OmegaConf/Hydra: layering, resolvers, and every config section.

-   :material-flask: **[Procedures](procedures.md)**

    The class hierarchy and a catalog of every built-in measurement.

-   :material-tune: **[Instruments](instruments.md)**

    Supported hardware, the InstrumentManager, and debug mode.

-   :material-format-list-numbered: **[Sequences](sequences.md)**

    Chaining procedures, common parameters and parameter sweeps.

-   :material-console: **[CLI & Scripts](cli-and-scripts.md)**

    The `laser_setup` command and the bundled utility scripts.

-   :material-database: **[Data & Output Files](data-and-output.md)**

    File naming, the CSV header format, and the SQLite database.

</div>
