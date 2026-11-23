"use strict";
window.spriteStackLayouts ??= {};
window.spriteStackLayouts[new URL(".", document.currentScript.src).href] = {
  "camera": {
    "pitch_deg": 24,
    "pixels_per_unit": 1.5,
    "base_pivot": [
      32,
      57
    ]
  },
  "clips": {
    "walk": {
      "rows": [
        "S",
        "SW",
        "W",
        "NW",
        "N",
        "NE",
        "E",
        "SE"
      ],
      "columns": 6,
      "cell": [
        64,
        64
      ],
      "anchor": [
        32,
        57
      ],
      "fps": 7,
      "suggested_forward_per_frame_model_units": 2.052,
      "stance": {
        "L": [
          0,
          1,
          2,
          3
        ],
        "R": [
          3,
          4,
          5,
          0
        ]
      }
    },
    "breathe": {
      "rows": [
        "S",
        "SW",
        "W",
        "NW",
        "N",
        "NE",
        "E",
        "SE"
      ],
      "columns": 4,
      "cell": [
        64,
        64
      ],
      "anchor": [
        32,
        57
      ],
      "fps": 3
    }
  }
};
