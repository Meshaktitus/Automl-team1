import numpy as np
import matplotlib.pyplot as plt  # type: ignore[reportMissingModuleSource]

xpoints = np.array([0, 6])
ypoints = np.array([0, 250])

plt.plot(xpoints, ypoints)

plt.title("My First Graph")
plt.xlabel("X Values")
plt.ylabel("Y Values")

plt.show()