Ran list files in workspace
Analyzed README.md:L1-24
Analyzed plan.md:L1-150
Analyzed plan.md:L151-250
Analyzed plan.md:L251-369
Ran inspect 2_2020_python_tutorial.ipynb cells
Ran find headings in tutorial notebook
Ran find headings in deflection angle notebook
Ran read Angular diameter distances section
Ran check python version in .venv
Ran list installed pip packages · Exited with code 127
Ran list packages using uv

### 1. Analysis of Your Master Plan (`plan.md`)

Your [plan.md](file:///home/heathcliff/Documents/GSOC/deeplance/LensingLectures-master/plan.md) is **exceptionally well-crafted** and provides the exact roadmap needed to go from zero astrophysics knowledge to a competitive contributor for **ML4SCI / DeepLense**:

1. **Rooted in the Academic Gold Standard**: Prof. Massimo Meneghetti's course *LensingLectures* (companion to his Springer textbook *Introduction to Gravitational Lensing*) is widely regarded as the most complete computational introduction to lensing.
2. **Prioritizes the True Lensing Pipeline**: Deep learning models in DeepLense (e.g., detecting dark matter subhalos, source reconstruction, parameter regression) cannot be designed as black boxes. You must understand the forward physics:
   $$\text{Source Galaxy } I_s(\vec{\beta}) \xrightarrow[\vec{\beta} = \vec{\theta} - \vec{\alpha}(\vec{\theta})]{\text{Ray Tracing}} \text{Lensed Image } I(\vec{\theta})$$
   Without understanding how deflection angles $\vec{\alpha}$, convergence $\kappa$, and shear $\gamma$ warp light, neural network predictions cannot be interpreted or validated.
3. **Pacing and Structure**: 
   - **Phase 0 & 1** build your vocabulary and the analytic mechanics of light bending.
   - **Phases 2, 3, & 4** demystify wave optics, the Jacobian distortion matrix, and Fast Fourier Transform (FFT) numerical solvers.
   - **Phases 5 & 6** hit the bullseye of DeepLense: dark matter substructures, Sérsic galaxy profiles, and PyTorch differentiable ray-tracing.

We will follow the **Antigravity Tutoring Protocol**:
- **Layer 1: Intuition** (plain-English visual analogies)
- **Layer 2: Physics & Mathematics** (clean, rigorous formulations)
- **Layer 3: Repository & Code Walkthrough** (inspecting real cells from the notebooks)
- **Layer 4: Deep Learning / PyTorch Connection** (how this maps to tensors, grids, and loss functions)
- **Layer 5: Checkpoint Challenge** (a short exercise to test your grasp)

---

## Phase 0: Mathematical & Astronomical Foundations

Since you have zero background in astronomy, we must first establish the coordinate system and distance definitions that astronomers and cosmologists use every day.

---

### 1. Angles on the Sky: The Astronomer's Coordinate System

#### The Intuition
When you look at a photograph of a galaxy or a gravitational lens taken by the Hubble Space Telescope (HST) or the James Webb Space Telescope (JWST), you cannot tell by eye how many light-years wide the galaxy is. You only know **how large an angle it subtends in your field of view**.

In astrophysics, all images and positions on the sky are measured in **angular units**.

```
Observer (Telescope)
      \       /
       \  θ  /   <--- Angular size θ (arcseconds)
        \   /
         \ /
       [Galaxy]  <--- Physical transverse size ξ (kiloparsecs)
```

#### The Units
- $1 \text{ circle} = 360^\circ$ (degrees)
- $1^\circ = 60'$ (arcminutes)
- $1' = 60''$ (arcseconds) $\implies 1^\circ = 3600''$

Gravitational lensing occurs on tiny angular scales:
- Strong lensing arcs and Einstein rings around galaxies are typically around **$1''$ to $2''$** (arcseconds) across.
- Around massive galaxy clusters, arcs can extend over **$10''$ to $30''$**.

To convert arcseconds to radians (using the small-angle approximation $\tan\theta \approx \theta$):
$$\theta \text{ [rad]} = \theta \text{ [arcsec]} \times \left(\frac{1^\circ}{3600''}\right) \times \left(\frac{\pi \text{ rad}}{180^\circ}\right) = \theta \text{ [arcsec]} \times \frac{\pi}{648{,}000}$$

$$\mathbf{1'' \approx 4.84814 \times 10^{-6} \text{ radians}}$$

#### Connection to Deep Learning & PyTorch
When you load an astronomical FITS image into PyTorch as a tensor of shape `(B, C, H, W)`:
- Pixels are not dimensionless abstract numbers; each pixel has a **pixel scale** (e.g., HST WFC3 is $0.04''/\text{pixel}$).
- If an Einstein ring is $30$ pixels in diameter, its physical angular radius is $\theta_E = 15 \times 0.04'' = 0.6''$.

---

### 2. Cosmological Redshift ($z$): Distance and Time

#### The Intuition
The universe is expanding. As light travels across billions of light-years of expanding space from a distant galaxy to our telescope, the fabric of spacetime stretches. Consequently, the wavelength of the light stretches with it.

Blue/UV light shifts toward red and infrared wavelengths. This is **Cosmological Redshift ($z$)**.

#### The Formula
$$1 + z = \frac{\lambda_{\text{observed}}}{\lambda_{\text{emitted}}} = \frac{a(t_{\text{observed}})}{a(t_{\text{emitted}})}$$

where $a(t)$ is the cosmic scale factor (the relative size of the universe at time $t$).

- $z = 0$: Right now, here on Earth.
- $z = 0.5$: Light emitted when the universe was $\frac{1}{1 + 0.5} = \frac{2}{3}$ of its current size.
- $z = 2.0$: Light emitted when the universe was $\frac{1}{3}$ of its current size.

#### The Lensing Configuration
In any gravitational lens system, there are always three primary redshifts:
$$z_{\text{observer}} = 0 < z_{\text{lens}} < z_{\text{source}}$$
- The **source galaxy** (background) is far away (e.g., $z_s = 2.0$).
- The **lens galaxy** (foreground deflector) sits somewhere between us and the source (e.g., $z_l = 0.5$).
- The **observer** is on Earth ($z = 0$).

---

### 3. Cosmological Distances: The Non-Euclidean Shock

#### The Intuition
In high school Euclidean geometry: if point A is $5 \text{ km}$ away and point B is $15 \text{ km}$ away in the same direction, the distance between A and B is simply $15 - 5 = 10 \text{ km}$.

**In an expanding relativistic universe, this is completely false!**

Because spacetime expands while light is travelling, astronomers define several distinct distances:
1. **Comoving Distance ($D_c$)**: Distance measured on a grid that expands along with the Hubble flow.
2. **Luminosity Distance ($D_L$)**: Governs the perceived brightness of supernovae and stars: $\text{Flux} = \frac{L}{4\pi D_L^2}$.
3. **Angular Diameter Distance ($D_A$)**: **The most important distance in gravitational lensing.**

#### Angular Diameter Distance ($D_A$)
$D_A$ is defined by the Euclidean relation between the physical transverse size of an object ($\xi$) and its observed angular diameter ($\theta$):
$$D_A \equiv \frac{\xi}{\theta}$$

Three crucial facts about Angular Diameter Distance:
1. **$D_{ls} \neq D_s - D_l$**:
   The distance from the lens to the source ($D_{ls}$) is **not** equal to the distance from us to the source ($D_s$) minus the distance to the lens ($D_l$). It must be calculated directly by integrating the cosmic expansion rate between $z_l$ and $z_s$.
2. **The Turnover Paradox**:
   In Euclidean space, as an object gets further away, it always looks smaller. 
   In our universe, $D_A(z)$ increases up to $z \approx 1.5 - 1.6$, and then **decreases**! Beyond $z \approx 1.6$, more distant galaxies actually appear *larger* on the sky because they emitted their light when the universe was much smaller and closer to our location in space.
3. **Relationship between distances**:
   $$D_L = (1 + z)^2 D_A$$

---

### 4. Repository Code Walkthrough: Astropy & Distances

Let's look at how Prof. Meneghetti demonstrates this in the repo's companion code: [Notebooks/3_2020_deflection_angle.ipynb](file:///home/heathcliff/Documents/GSOC/deeplance/LensingLectures-master/Notebooks/3_2020_deflection_angle.ipynb#L40).

```python
from astropy.cosmology import FlatLambdaCDM
import numpy as np

# Set standard cosmological parameters:
# H0 = 70 km/s/Mpc (expansion rate)
# Om0 = 0.3 (30% matter, 70% dark energy / cosmological constant Lambda)
co = FlatLambdaCDM(H0=70, Om0=0.3)

zl = 0.5  # Lens redshift
zs = 2.0  # Source redshift

dl = co.angular_diameter_distance(zl)
ds = co.angular_diameter_distance(zs)
dls = co.angular_diameter_distance_z1z2(zl, zs)

print(f"Distance to lens (D_l):                 {dl:.2f}")
print(f"Distance to source (D_s):               {ds:.2f}")
print(f"Naive Euclidean subtraction (D_s - D_l): {ds - dl:.2f}")
print(f"True Relativistic D_ls:                 {dls:.2f}")
```

If you evaluate this, you find:
- $D_l(z=0.5) \approx 1314 \text{ Mpc}$
- $D_s(z=2.0) \approx 1765 \text{ Mpc}$
- Naive subtraction: $D_s - D_l \approx 451 \text{ Mpc}$
- **True Angular Diameter Distance $D_{ls} \approx 1113 \text{ Mpc}$!**

Notice that $1113 \text{ Mpc}$ is more than **double** the naive subtraction $451 \text{ Mpc}$. If you used naive Euclidean distances in a lens model, your calculated lens masses and Einstein radii would be wrong by over $100\%$!

---

### 5. Astropy Units & Constants: Writing Bug-Free Physics Code

In astrophysics, formulas involve quantities with radically different units:
- Gravitational constant: $G \approx 6.674 \times 10^{-11} \text{ m}^3\text{ kg}^{-1}\text{ s}^{-2}$
- Speed of light: $c \approx 2.998 \times 10^8 \text{ m/s}$
- Masses in Solar Masses ($M_\odot \approx 1.989 \times 10^{30} \text{ kg}$)
- Distances in Megaparsecs ($1 \text{ Mpc} \approx 3.086 \times 10^{22} \text{ meters}$)

In `Notebooks/2_2020_python_tutorial.ipynb`, Meneghetti emphasizes using `astropy.units` and `astropy.constants` so you never have to manually track unit conversion factors:

```python
from astropy import constants as const
from astropy import units as u

# Solar mass
M = 1e12 * u.Msun  # 1 trillion solar masses (typical galaxy halo)

# Distance in Mpc
distance = 1000 * u.Mpc

# Physical quantity with automatic dimension check
c = const.c
G = const.G
```

---

### 6. Phase 0 Checkpoint Challenge

To make sure these concepts are crystal clear before we jump into **Phase 1 (Einstein Deflection Angle & The Lens Equation)**, try this quick challenge:

#### Question 1 (Conceptual)
If a galaxy at redshift $z = 0.5$ has a physical diameter of $20 \text{ kpc}$ ($1 \text{ Mpc} = 1000 \text{ kpc}$) and its angular diameter distance is $D_A = 1300 \text{ Mpc}$, calculate its angular size $\theta$ on the sky in **arcseconds** ($''$).

#### Question 2 (Conceptual)
Why is the angular diameter distance $D_{ls}$ between a lens at $z_l$ and a source at $z_s$ strictly **different** from $D_s - D_l$?

#### Question 3 (Coding Mini-Task)
Using Python and `astropy.cosmology.FlatLambdaCDM(H0=70, Om0=0.3)`, calculate the ratio $\frac{D_{ls}}{D_s}$ for a lens at $z_l = 0.3$ and a source at $z_s = 1.2$. 
*(Hint: In Phase 1, you will discover that this distance ratio $\frac{D_{ls}}{D_s}$ directly determines the lensing efficiency!)*

Give these three a shot (or tell me your answers/thoughts), and we will immediately dive into **Phase 1: General Relativity, Deflection Angles, and Point Mass Lensing**!
