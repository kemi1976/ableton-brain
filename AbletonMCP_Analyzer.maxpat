{
  "patcher": {
    "fileversion": 1,
    "appversion": "8.6.2",
    "classnamespace": "box",
    "rect": [100, 100, 800, 600],
    "bglocked": 0,
    "openinpresentation": 0,
    "default_fontsize": 12,
    "default_fontface": 0,
    "default_fontname": "Arial",
    "gridonopen": 0,
    "gridsize": [15, 15],
    "gridsnaponopen": 0,
    "objectsnaponopen": 0,
    "statusbarvisible": 2,
    "toolbarvisible": 1,
    "boxanimatetime": 200,
    "implicittemplate": 0,
    "description": "AbletonMCP Analyzer - Real-time audio analysis for Ableton Live. Measures LUFS, true peak, stereo correlation, spectral bands, tempo, key.",
    "tags": ["audio", "analysis", "metering", "loudness", "mcp"],
    "boxes": [
      {
        "box": {
          "maxclass": "newobj",
          "text": "live.thisdevice",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [50, 50, 100, 22],
          "id": "obj-1",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "live.path live_set",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [50, 100, 100, 22],
          "id": "obj-2",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "live.observer @property \"tracks\"",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [50, 150, 180, 22],
          "id": "obj-3",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "meter~",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [50, 250, 60, 60],
          "presentation_rect": [50, 50, 60, 60],
          "id": "obj-4",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial",
          "presentation": 1
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "loudness~ @standard BS1770 @mode integrated",
          "numinlets": 2,
          "numoutlets": 3,
          "patching_rect": [50, 350, 200, 22],
          "id": "obj-5",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "loudness~ @standard BS1770 @mode momentary",
          "numinlets": 2,
          "numoutlets": 3,
          "patching_rect": [50, 400, 200, 22],
          "id": "obj-6",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "loudness~ @standard BS1770 @mode shortterm",
          "numinlets": 2,
          "numoutlets": 3,
          "patching_rect": [50, 450, 200, 22],
          "id": "obj-7",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "truepeak~",
          "numinlets": 2,
          "numoutlets": 2,
          "patching_rect": [300, 250, 100, 22],
          "id": "obj-8",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "stereocorr~",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [300, 300, 100, 22],
          "id": "obj-9",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "fft~ 2048 512 0 1",
          "numinlets": 1,
          "numoutlets": 3,
          "patching_rect": [500, 250, 80, 22],
          "id": "obj-10",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "p spectral_bands",
          "numinlets": 1,
          "numoutlets": 7,
          "patching_rect": [500, 300, 100, 22],
          "id": "obj-11",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "tempo~",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [50, 500, 80, 22],
          "id": "obj-12",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "key~",
          "numinlets": 1,
          "numoutlets": 2,
          "patching_rect": [50, 530, 80, 22],
          "id": "obj-13",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "pack",
          "numinlets": 12,
          "numoutlets": 1,
          "patching_rect": [200, 200, 100, 22],
          "id": "obj-14",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "udpsend 127.0.0.1 9878",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [200, 250, 150, 22],
          "id": "obj-15",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "newobj",
          "text": "metro 1000",
          "numinlets": 2,
          "numoutlets": 1,
          "patching_rect": [50, 200, 60, 22],
          "id": "obj-16",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "toggle",
          "numinlets": 1,
          "numoutlets": 1,
          "patching_rect": [50, 170, 20, 20],
          "id": "obj-17",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "AbletonMCP Analyzer - Send audio metrics via OSC every second",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [50, 20, 300, 22],
          "id": "obj-18",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "LUFS (Integrated, Momentary, Short-term)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [50, 330, 200, 22],
          "id": "obj-19",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "True Peak & Stereo Correlation",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [300, 230, 200, 22],
          "id": "obj-20",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "7-Band Spectrum (Sub, Bass, Low-Mid, Mid, High-Mid, High, Air)",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [500, 230, 250, 22],
          "id": "obj-21",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      },
      {
        "box": {
          "maxclass": "comment",
          "text": "Tempo & Key Detection",
          "numinlets": 1,
          "numoutlets": 0,
          "patching_rect": [50, 480, 150, 22],
          "id": "obj-22",
          "fontsize": 12,
          "fontface": 0,
          "fontname": "Arial"
        }
      }
    ],
    "lines": [
      {
        "patchline": {
          "source": ["obj-17", 0],
          "destination": ["obj-16", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-16", 0],
          "destination": ["obj-14", 0]
        }
      },
      {
        "patchline": {
          "source": ["obj-4", 0],
          "destination": ["obj-14", 1]
        }
      },
      {
        "patchline": {
          "source": ["obj-5", 0],
          "destination": ["obj-14", 2]
        }
      },
      {
        "patchline": {
          "source": ["obj-6", 0],
          "destination": ["obj-14", 3]
        }
      },
      {
        "patchline": {
          "source": ["obj-7", 0],
          "destination": ["obj-14", 4]
        }
      },
      {
        "patchline": {
          "source": ["obj-8", 0],
          "destination": ["obj-14", 5]
        }
      },
      {
        "patchline": {
          "source": ["obj-9", 0],
          "destination": ["obj-14", 6]
        }
      },
      {
        "patchline": {
          "source": ["obj-11", 0],
          "destination": ["obj-14", 7]
        }
      },
      {
        "patchline": {
          "source": ["obj-11", 1],
          "destination": ["obj-14", 8]
        }
      },
      {
        "patchline": {
          "source": ["obj-11", 2],
          "destination": ["obj-14", 9]
        }
      },
      {
        "patchline": {
          "source": ["obj-11", 3],
          "destination": ["obj-14", 10]
        }
      },
      {
        "patchline": {
          "source": ["obj-11", 4],
          "destination": ["obj-14", 11]
        }
      },
      {
        "patchline": {
          "source": ["obj-12", 0],
          "destination": ["obj-14", 12]
        }
      },
      {
        "patchline": {
          "source": ["obj-13", 0],
          "destination": ["obj-14", 13]
        }
      },
      {
        "patchline": {
          "source": ["obj-14", 0],
          "destination": ["obj-15", 0]
        }
      }
    ],
    "subpatches": [
      {
        "name": "spectral_bands",
        "boxes": [
          {
            "box": {
              "maxclass": "inlet",
              "numinlets": 1,
              "numoutlets": 0,
              "patching_rect": [50, 50, 30, 30],
              "id": "sub-1"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "cartopol",
              "numinlets": 2,
              "numoutlets": 2,
              "patching_rect": [50, 100, 60, 22],
              "id": "sub-2"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "split 7",
              "numinlets": 1,
              "numoutlets": 2,
              "patching_rect": [50, 150, 60, 22],
              "id": "sub-3"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [50, 200, 60, 22],
              "id": "sub-4"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [150, 200, 60, 22],
              "id": "sub-5"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [250, 200, 60, 22],
              "id": "sub-6"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [350, 200, 60, 22],
              "id": "sub-7"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [450, 200, 60, 22],
              "id": "sub-8"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [550, 200, 60, 22],
              "id": "sub-9"
            }
          },
          {
            "box": {
              "maxclass": "newobj",
              "text": "mean~",
              "numinlets": 1,
              "numoutlets": 1,
              "patching_rect": [650, 200, 60, 22],
              "id": "sub-10"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [50, 250, 30, 30],
              "id": "sub-11"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [150, 250, 30, 30],
              "id": "sub-12"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [250, 250, 30, 30],
              "id": "sub-13"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [350, 250, 30, 30],
              "id": "sub-14"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [450, 250, 30, 30],
              "id": "sub-15"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [550, 250, 30, 30],
              "id": "sub-16"
            }
          },
          {
            "box": {
              "maxclass": "outlet",
              "numinlets": 0,
              "numoutlets": 1,
              "patching_rect": [650, 250, 30, 30],
              "id": "sub-17"
            }
          }
        ],
        "lines": [
          {
            "patchline": {
              "source": ["sub-1", 0],
              "destination": ["sub-2", 0]
            }
          },
          {
            "patchline": {
              "source": ["sub-2", 1],
              "destination": ["sub-3", 0]
            }
          },
          {
            "patchline": {
              "source": ["sub-3", 0],
              "destination": ["sub-4", 0]
            }
          },
          {
            "patchline": {
              "source": ["sub-3", 1],
              "destination": ["sub-5", 0]
            }
          }
        ]
      }
    ]
  }
}