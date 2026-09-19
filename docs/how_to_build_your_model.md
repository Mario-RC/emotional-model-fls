# How To Build Your Model

This project separates the fuzzy engine from the emotional model configuration.
You can define your own model in a YAML file and load it with:

```bash
emotional-model-fls --config path/to/your_model.yaml --steps 1
```

or from Python:

```python
from emotional_model_fls.runtime import EmotionalModel

model = EmotionalModel(config_path="path/to/your_model.yaml")
outputs = model.step()
```

## Config Sections

### `variables`

Each variable defines:

- `control_name`: name used inside `skfuzzy`.
- `universe`: numeric range passed to `numpy.arange(start, stop, 1)`.
- `terms`: fuzzy labels and their membership functions.

Supported membership functions:

```yaml
kind: tri
points: [left, peak, right]
```

```yaml
kind: trap
points: [left, left_top, right_top, right]
```

### `input_aliases`

Feedback controllers often need the previous value of an output as a new input.
For example, the runtime can expose `mood` as `_mood`:

```yaml
input_aliases:
  mood_input:
    source: mood
    control_name: _mood
```

The alias reuses the source variable universe and terms, but changes the
`control_name`.

### `rules`

Every rule set declares:

- `output`: output variable key.
- `dimensions`: input variables and the terms to combine.
- one of `default`, `items` or `table`.

The compact style is recommended for public examples. The `DEMO_*` labels below
are synthetic examples, not rules or calibration from the research model:

```yaml
rules:
  mood:
    output: mood
    dimensions:
      - [battery, [DEMO_1, DEMO_2, DEMO_3]]
      - [mood, [DEMO_1, DEMO_2, DEMO_3, DEMO_4, DEMO_5]]
    default: DEMO_3
    overrides:
      - when: {battery: DEMO_1}
        then: DEMO_5
      - when: {battery: DEMO_3, mood: DEMO_5}
        then: DEMO_1
```

`overrides` may omit dimensions. Omitted dimensions act as wildcards.

Explicit rules are also supported:

```yaml
rules:
  heartbeat:
    output: heartbeat
    dimensions:
      - [alertness, [DEMO_1, DEMO_2, DEMO_3]]
    items:
      - when: {alertness: DEMO_1}
        then: DEMO_2
      - when: {alertness: DEMO_2}
        then: DEMO_2
      - when: {alertness: DEMO_3}
        then: DEMO_2
```

Full tables are supported for small models, but avoid publishing calibrated
private matrices if those are part of your intellectual property.

## Optional Runtime Settings

The existing API and demo work without a `runtime` section. To use your own
calibration, add any of these optional groups to the same JSON/YAML config:

| Group | Keys and meaning |
| --- | --- |
| `sensor_ranges` | Raw sensor names, each mapped to an inclusive `[minimum, maximum]` pair |
| `sensor_defaults` | Initial readings, keyed by raw sensor name |
| `initial_states` | Initial feedback values for `mood`, `alertness`, `interest`, `affective`, `expectancy` |
| `delays` | Non-negative smoothing constants for those internal states |
| `sensor_weights` | Weights for the two antennas, three head buttons and two body buttons, using their raw sensor names |
| `processing` | `antennas_frequency_time`, `head_buttons_frequency_time`, `flashlights_time`, `flashlights_threshold_value`, `flashlights_threshold`, `flashlights_debounce_steps`, `frequency_scale` |

For `battery`, `speech`, `light` and `glucose`, sensor bounds automatically follow
the variable universe: `[start, stop - 1]`. An explicit `sensor_ranges` entry may
narrow those bounds. Raw antenna and button ranges otherwise keep their demo
defaults because several raw sensors contribute to one fuzzy variable.

Unspecified settings retain demo values. If a default sensor reading or initial
state lies outside a customized range, its fallback is the midpoint of that
range; explicit values outside their range are rejected. Window sizes must be
positive integers, debounce steps a non-negative integer, and frequency scale
positive. All supplied numbers must be finite. Unknown setting names are errors.

Choose aggregation weights and frequency scales consistently with the universes
of the derived inputs. Keep your research configuration outside the public
repository; the original rules, FIS and variable values must be requested from
the project owner.

## Required Public Runtime Keys

The default runtime expects these variable keys:

- Sensor and derived inputs: `battery`, `antennas`, `antennas_frequency`,
  `speech`, `light`, `glucose`, `head_buttons`, `body_buttons`,
  `head_buttons_frequency`, `flashlights_frequency`.
- Internal states: `mood`, `alertness`, `interest`, `affective`, `expectancy`.
- Expressions: `body_speed`, `general_state`, `heartbeat`.
- Feedback aliases: `mood_input`, `alertness_input`, `interest_input`,
  `affective_input`, `expectancy_input`.

If you want different keys or a different dependency graph, create your own
runtime class or adapt `state.py` and `expressions.py`.

## Privacy Checklist

Before publishing a repository:

- Remove real rule spreadsheets.
- Remove calibrated `fuzzy_specs.py` files.
- Remove generated plots from the private model.
- Remove real experiment scripts and outputs.
- Search for private terms, filenames and absolute paths.
- Create the Git repository only after the cleaned tree is ready.
