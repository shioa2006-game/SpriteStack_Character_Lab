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
      "fps": 9,
      "suggested_forward_per_frame_model_units": 1.824,
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
      },
      "stopping_poses": [
        {
          "after_frame": 1,
          "support": "L",
          "root_delta_xyz": [
            0.3599999999999999,
            1.232,
            4.440892098500626e-16
          ]
        },
        {
          "after_frame": 4,
          "support": "R",
          "root_delta_xyz": [
            -0.3599999999999999,
            0.5920000000000001,
            4.440892098500626e-16
          ]
        }
      ]
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
    },
    "attack": {
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
      "columns": 10,
      "cell": [
        104,
        104
      ],
      "anchor": [
        52,
        77
      ],
      "fps": 10,
      "durations_ms": [
        70,
        95,
        105,
        145,
        55,
        60,
        125,
        100,
        95,
        70
      ],
      "phase_names": [
        "ready",
        "draw back",
        "raise",
        "cocked",
        "drive",
        "release",
        "follow through",
        "reach pouch",
        "draw next",
        "ready"
      ]
    }
  }
};
