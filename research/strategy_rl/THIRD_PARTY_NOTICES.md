# Independent RL experiment dependencies

This package installs public dependencies into its separate local environment.
No third-party runtime binaries are vendored in the repository. The exact
observed versions are recorded in `requirements.lock`.

- PyTorch 2.10.0: [upstream](https://github.com/pytorch/pytorch), BSD-style terms
  and bundled third-party notices preserved verbatim in
  [PyTorch-LICENSE.txt](licenses/PyTorch-LICENSE.txt).
- NumPy 2.3.5: [upstream](https://github.com/numpy/numpy), BSD-style terms and
  bundled notices preserved in [NumPy-LICENSE.txt](licenses/NumPy-LICENSE.txt).
- pytest 9.0.2 is used for tests under its MIT license; it is not vendored.

The retained checkpoints are newly trained Tachyon neural parameters from this
authored abstract environment. They contain no manufacturer CAD or private
robotics implementation. Software licenses do not grant rights to VEX assets.
