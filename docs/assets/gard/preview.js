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
      },
      "stopping_poses": [
        {
          "after_frame": 1,
          "support": "L",
          "root_delta_xyz": [
            0.3599999999999999,
            1.3459999999999999,
            4.440892098500626e-16
          ]
        },
        {
          "after_frame": 4,
          "support": "R",
          "root_delta_xyz": [
            -0.3599999999999999,
            0.706,
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
      "columns": 9,
      "cell": [
        84,
        84
      ],
      "anchor": [
        42,
        67
      ],
      "fps": 10,
      "durations_ms": [
        60,
        90,
        150,
        190,
        50,
        110,
        80,
        140,
        90
      ],
      "phase_names": [
        "guard",
        "brace shield",
        "draw back",
        "high hold",
        "downswing",
        "impact",
        "settle",
        "lift clear",
        "guard"
      ]
    }
  }
};
