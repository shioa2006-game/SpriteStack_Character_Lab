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
      "fps": 11,
      "suggested_forward_per_frame_model_units": 1.406,
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
            0.3600000000000001,
            1.0230000000000004,
            4.440892098500626e-16
          ]
        },
        {
          "after_frame": 4,
          "support": "R",
          "root_delta_xyz": [
            -0.3600000000000001,
            0.383,
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
        80,
        80
      ],
      "anchor": [
        40,
        65
      ],
      "fps": 10,
      "durations_ms": [
        40,
        60,
        70,
        90,
        100,
        40,
        60,
        80,
        50
      ],
      "phase_names": [
        "ready",
        "raise bow",
        "nock",
        "draw",
        "aim",
        "loose",
        "recoil",
        "lower bow",
        "ready"
      ]
    }
  }
};
