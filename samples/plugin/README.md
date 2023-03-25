# Plugin Sample

This sample project demonstrates how to write your own plugins for bip.

A plugin is nothing different that a Python file present in your source
directory containing 3 functions:

* `clean`, which removes any outputs of previous builds.
* `should_build`, which checks whether we need to build or rebuild. For example,
    this would return `True` if the files this plugin is responsible for have
    changed since last build or the output files are missing.
* `build`, which is called only if `should_build` returns `True`.

Plugins have complete access to all the information provided by the recipe file
via the `build.Info` object provided to each function. Among others, the object
contains:

* `root_dir`, the directory of the project.
* `src_dir`, the *base* source directory, not the source of this plugin.
* `out_dir`, the final output directory. (e.g. `dll`s, `jar`s)
* `obj_dir`, the temporary output directory. (e.g. MSVC `obj`s, Java `class`es)
* `incl_dir`, the directories to add to the C/C++ include search path.
