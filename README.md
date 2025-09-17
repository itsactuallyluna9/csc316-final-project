# CSC316 Final Project

A model that's supposed to beat False Knight from the game Hollow Knight using reenforcement learning.

(Currently, it... doesn't beat False Knight.)

## Demo

<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/us5IEG1MozQ?si=JjZS0agrOHaZ-zuk" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

(or, see https://youtu.be/us5IEG1MozQ)

## Features

- A live status bar, showing the current score, episode, and inputs.
- Reading health information from the game via Computer Vision (The Knight) and Object Detection (False Knight).
- Automatic recording of training data using OBS.

## Installation / Running
For easiest installation, make sure you have UV installed.

```bash
$ uv run csc_316_final_project
```

## Credits

* Luna (@itsactuallyluna9) - Model (the entire thing), Interop, Monitor Status Bar
* Arjay (@arjay464) - CV & Object Detection, Keyboard Output, OBS Support
