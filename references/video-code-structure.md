# Component and animation source for each recording

Every video reconstruction delivers a runnable project with separate `components/` and `animations/` source directories. Generate the actual components and motion implementations needed by that recording. These are part of the generated project, outside the skill folder. Iterate on the same files when refining the same recording.

Use the existing project's framework, language, module conventions and directory roots. For example, React can use `src/components/` and `src/animations/`, Vue can use `.vue` components and animation modules, and a new plain HTML/CSS/JS project can use this structure:

```text
project/
  index.html
  src/
    main.js
    components/
      VideoPage.js
      ActionButton.js
      DetailDrawer.js
      detail-drawer.css
    animations/
      drawer-motion.js
      backdrop-motion.js
    styles/
      tokens.css
      page.css
  assets/
  interaction-spec.json
  design-qa.md
```

Names above illustrate a recording with a button and drawer. Name files after the actual screens, controls and transitions; do not generate unrelated examples. In an existing project, use its component/animation directories and a feature subdirectory where needed. Multiple unrelated recordings get separate project or feature scopes; multiple recordings of the same feature can share implementations while retaining their evidence references.

## Responsibilities and wiring

- Components contain editable semantic markup, visual styling, inputs/state and event hooks. Split meaningful screens, repeated controls and independently changing regions. Reuse a component for repeated instances rather than duplicating markup.
- Animation files contain the recording-specific keyframes, duration, easing, displacement and animation/gesture execution. Use CSS, browser animation APIs or the project's existing animation library as appropriate. Parameters must be adjustable at their definition, and components import or reference these files instead of duplicating motion inline.
- The page entry assembles the components; components invoke the corresponding animation code on actual user actions. CSS files must be linked/imported and modules must be loaded. Existing state ownership and component cleanup conventions still apply.
- Opening, closing, cancellation and repeat actions should use the same state and motion definitions. Preserve observed behavior and label inferred motion parameters. When there is no demonstrated animation, provide an explicit motion-disabled configuration in `animations/` that the components consume, without adding decorative motion.
- Keep components and animation files specific to this reconstruction and usable within the project. Empty directories, unused files, generic animation catalogs and documentation-only stubs do not satisfy the output requirement.

## Evidence and delivery

Record a compact mapping in `design-qa.md`: state/transition ID → component file → animation file (if applicable) → source frames/time range → actual verification result. Existing `interaction-spec.json` IDs supply the keys; a second parallel evidence format is unnecessary.

Check the page uses the delivered modules and styles in the real browser, assets/imports load, controls reach their intended states, and animation timing matches the inspected frames. Include both directories in the delivered source. Apply the existing full-page, regional and motion checks to the assembled project.

This video output requirement overrides upstream single-file HTML or inline-script guidance. For plain HTML use linked CSS and JavaScript modules served from the local preview. `finalize` only extracts an HTML entry document when needed; it does not package, inline, or replace the component/animation files. Screenshot-only tasks retain their existing output conventions.
