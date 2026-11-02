# Mysteries posed to Euresis

The mysteries (questions only) were written by a person; everything below was produced by Euresis from its own knowledge base, reasoning engines, simulators and data analysis. Literature novelty checks could not run in this environment (no network access to paper databases).

## Hot-Jupiter radius anomaly

> Why are many giant planets orbiting close to their stars larger in radius than cooling models predict, and what law links their radius to the stellar flux they receive and their mass?

*Euresis approached it through:* Cyclotron radius, Nuclear radius, Stellar luminosity, Schwarzschild radius, Law of Laplace (blood vessel), Photon sphere radius

- Scale: radius ~ sqrt(G)*sqrt(hbar)/c^(3/2) ≈ 1.616e-35 (SI)
- Scale: radius ~ sqrt(G)*e/(c^2*sqrt(epsilon_0)) ≈ 4.894e-36 (SI)
- Scale: radius ~ sqrt(G)*epsilon_0^(3/2)*hbar^2/e^3 ≈ 5.820e-34 (SI)
- Dimensionless number: a_0/R_earth ≈ 8.297e-18
- Dimensionless number: R_earth^2*c^4*epsilon_0/(G*e^2) ≈ 1.698e+84
- Dimensionless number: G*hbar/(R_earth^2*c^3) ≈ 6.421e-84
- Composition: q = c^2*v/(2*B*G)  [candidate (not in knowledge base, untested); via Cyclotron radius → Schwarzschild radius]
- Composition: q = c^2*v/(3*B*G)  [candidate (not in knowledge base, untested); via Cyclotron radius → Photon sphere radius]
- Composition: T_w = P_pressure*m*v/(B*q)  [candidate (not in knowledge base, untested); via Cyclotron radius → Law of Laplace (blood vessel)]
- Composition: T_w = 2*G*P_pressure*m/c^2  [candidate (not in knowledge base, untested); via Schwarzschild radius → Law of Laplace (blood vessel)]
- Composition: T_w = 3*G*P_pressure*m/c^2  [candidate (not in knowledge base, untested); via Law of Laplace (blood vessel) → Photon sphere radius]
- Composition: T_w = A_mass^(1/3)*P_pressure*r_0  [candidate (not in knowledge base, untested); via Nuclear radius → Law of Laplace (blood vessel)]
- Data: Searched 18 candidate laws on 620 real giant planets (Open Exoplanet Catalogue).
- Data: Best law (BIC): Euresis: R = [a·x^p·exp(b·x^r)](F) · M^c — cross-validated error 0.0989 dex vs 0.1117 dex for a simple power law in mass and flux.
- Data: Radius rises with flux but saturates and turns over at the highest flux (parameters 0.962, -0.0402, 0.0614, 0.315, -0.0473).
- Data: Unexplained residual correlates with host-star metallicity (ρ = -0.145): metal-rich systems host denser giant planets.

**Verdict:** Partial progress: found a better-fitting empirical law in real data and a residual trend; the physical mechanism remains unexplained. Literature novelty unchecked.

## Why is gravity so weak?

> Why is the gravitational force between elementary particles so much weaker than the electromagnetic force, and what sets the ratio of the Planck mass to the proton mass?

*Euresis approached it through:* Centripetal force, Newton's second law, Chandrasekhar limit, Lorentz force (magnetic, perpendicular), Kinetic friction, Archimedes' principle

- Dimensionless number: a_0^2*c^4*epsilon_0/(G*e^2) ≈ 1.169e+50
- Dimensionless number: G*hbar/(a_0^2*c^3) ≈ 9.329e-50
- Dimensionless number: G*m_e/(a_0*c^2) ≈ 1.278e-47
- Analogy: q = q1*q2/(q1 + q2)  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Coulomb's law → Reduced mass]
- Composition: rho_density = m*v^2/(V*g*r)  [candidate (not in knowledge base, untested); via Centripetal force → Archimedes' principle]
- Composition: F_centripetal = 0.774402486238505*v^2*(c*ħ/G)^(3/2)/(m_p^2*r)  [candidate (not in knowledge base, untested); via Centripetal force → Chandrasekhar limit]
- Composition: I_current = m*v^2/(B*L_length*r)  [candidate (not in knowledge base, untested); via Centripetal force → Force on a current-carrying wire]
- Composition: a = B*q*v/m  [candidate (not in knowledge base, untested); via Newton's second law → Lorentz force (magnetic, perpendicular)]
- Composition: q = g*m/(B*v)  [candidate (not in knowledge base, untested); via Lorentz force (magnetic, perpendicular) → Weight]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Scale of quantum gravity

> At what length, energy, time and temperature must gravity and quantum mechanics merge, and which physical systems come closest to that regime?

*Euresis approached it through:* Particle in a box energy levels, Energy-time uncertainty, Diffusion time, Thermal diffusion time, Mean kinetic energy of a gas molecule, Quantum harmonic oscillator levels

- Scale: temperature ~ energy/k_B
- Scale: temperature ~ h/(k_B*time)
- Scale: temperature ~ hbar/(k_B*time)
- Dimensionless number: hbar/h ≈ 0.159
- Analogy: F = m*v/t  [candidate (not in knowledge base, untested); via Energy stored in an inductor → Kinetic energy → Self-induced EMF]
- Composition: L_length = h*n_quantum/(2*m*v)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Kinetic energy]
- Composition: E_energy = h*n_quantum*v/(4*L_length)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Kinetic energy]
- Analogy: v = K/(L_length*f_c*m)  [candidate (not in knowledge base, untested); via Bernoulli dynamic pressure → Kinetic energy → Geostrophic wind]
- Composition: omega_angular = m*v^2/(ħ*(2*n_quantum + 1))  [candidate (not in knowledge base, untested); via Quantum harmonic oscillator levels → Kinetic energy]
- Composition: a = alpha_d*dv/L_length^2  [candidate (not in knowledge base, untested); via Thermal diffusion time → Average acceleration]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Black hole information

> How much information can a black hole hold, how hot is it, and how long does it take to evaporate, given its entropy and Hawking temperature?

*Euresis approached it through:* Hawking temperature of a black hole, Bekenstein-Hawking entropy, Binary entropy function, Clausius entropy, Boltzmann entropy, Landauer limit

- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*k_B) ≈ 1.417e+32 (SI)
- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*entropy)
- Composition: E = c^3*ħ*log(2)/(8*π*G*m)  [candidate (not in knowledge base, untested); via Hawking temperature of a black hole → Landauer limit]
- Composition: dS = 8*π*G*Q*k_B*m/(c^3*ħ)  [candidate (not in knowledge base, untested); via Hawking temperature of a black hole → Clausius entropy]
- Composition: I_information = 2*π*T_temperature*dS*r/(c*ħ*log(2))  [candidate (not in knowledge base, untested); via Clausius entropy → Bekenstein bound]
- Composition: I_information = 2*π*T_temperature*k_B*r/(c*ħ)  [candidate (not in knowledge base, untested); via Landauer limit → Bekenstein bound]
- Composition: E = -c*ħ*log(p_probability)/(2*π*r)  [candidate (not in knowledge base, untested); via Shannon information of an outcome → Bekenstein bound]
- Composition: A = 4*G*ħ*log(N_number)/c^3  [candidate (not in knowledge base, untested); via Bekenstein-Hawking entropy → Boltzmann entropy]

**Verdict:** Quantified, not solved: Euresis derived the characteristic scales the answer must involve and connected them to known laws. These frame the mystery; they do not explain its mechanism.

## Dark matter in galaxies

> Why do stars in the outer parts of galaxies orbit faster than the visible mass and gravity predict, and what density of unseen matter would explain flat rotation velocity?

*Euresis approached it through:* Density, Mass flow rate, Cyclotron radius, Surface gravity, Orbital period of a circular orbit, Innermost stable circular orbit

- Scale: velocity ~ sqrt(G)*density^(1/6)*mass^(1/3)
- Dimensionless number: g_n/(Omega_E*c) ≈ 4.486e-04
- Analogy: q = q1*q2/(q1 + q2)  [candidate (not in knowledge base, untested); via Surface gravity → Field of a point charge → Reduced mass]
- Composition: g = G*V*rho_density/r^2  [candidate (not in knowledge base, untested); via Density → Surface gravity]
- Composition: g = c^2/(6*r)  [candidate (not in knowledge base, untested); via Surface gravity → Innermost stable circular orbit]
- Composition: q = v^3/(B*G)  [candidate (not in knowledge base, untested); via Cyclotron radius → Circular orbital velocity]
- Composition: T = 12*π*G*m/(c^2*v_orbital)  [candidate (not in knowledge base, untested); via Orbital period of a circular orbit → Innermost stable circular orbit]
- Composition: g = B*G*q/(r*v)  [candidate (not in knowledge base, untested); via Cyclotron radius → Surface gravity]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Dark energy and the cosmological constant

> What energy density does the expansion rate of the universe imply, and how does it compare with the vacuum energy density at the Planck scale?

*Euresis approached it through:* Energy density of magnetic field, Energy density of electric field, Elastic energy density, Margolus-Levitin bound, Fermi energy of a free electron gas, Photon energy from wavelength

- Scale: energy density ~ density/(epsilon_0*mu_0)
- Dimensionless number: E_R^2*G*epsilon_0/(c^4*e^2) ≈ 1.354e-53
- Dimensionless number: c^5*h/(E_R^2*G) ≈ 5.059e+54
- Dimensionless number: c^5*hbar/(E_R^2*G) ≈ 8.052e+53
- Composition: rate = 2*c^2*m/(π*ħ)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Mass-energy equivalence]
- Composition: E_rest = h*rate  [candidate (not in knowledge base, untested); via Bremermann's limit → Mass-energy equivalence]
- Composition: B = σ_s*√(μ₀/Y)  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Elastic energy density]
- Composition: E = π*c^2*ħ*m/(2*h)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Bremermann's limit]
- Composition: E_electric = σ_s*√(1/(Y*ε₀))  [candidate (not in knowledge base, untested); via Energy density of electric field → Elastic energy density]
- Composition: f_frequency = c^2*m/h  [candidate (not in knowledge base, untested); via Planck-Einstein relation → Mass-energy equivalence]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Solar coronal heating

> Why is the solar corona millions of kelvin hotter than the surface, and could magnetic energy density in the solar atmosphere supply the heat?

*Euresis approached it through:* Solar constant, Energy density of magnetic field, Mass-luminosity relation (main sequence), Magnetic dipole energy, Magnetic flux, Magnetic pressure

- Dimensionless number: R_sun/AU ≈ 0.00465
- Dimensionless number: L_sun*yr^3/(AU^2*M_sun) ≈ 2.703e-04
- Composition: Phi_magnetic = A*U/mu_magnetic  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Magnetic flux]
- Composition: L_latent = c_specific*dT  [candidate (not in knowledge base, untested); via Latent heat → Specific heat]
- Composition: B = c_specific*dT*m/mu_magnetic  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Specific heat]
- Composition: L_latent = B*mu_magnetic/m  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Latent heat]
- Composition: C = B*mu_magnetic/dT  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Heat capacity]
- Composition: C = L_latent*m/dT  [candidate (not in knowledge base, untested); via Heat capacity → Latent heat]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Climate sensitivity

> How much does Earth's surface temperature rise for a doubling of carbon dioxide, and how much do feedbacks such as ice albedo amplify it?

*Euresis approached it through:* Planetary equilibrium temperature, Capillary rise (Jurin's law), Doubling time, Young-Laplace (sphere)

- Dimensionless number: a_s/(M_earth*Omega_E^2*R_earth^2) ≈ 2.208e-42
- Composition: P_pressure = g*h_height*rho_density/cos(theta)  [candidate (not in knowledge base, untested); via Capillary rise (Jurin's law) → Young-Laplace (sphere)]
- Experiment: Energy-balance model, CO₂ 280→560 ppm, ice-albedo feedback off: warming 1.11 K (baseline 287.8 K).
- Experiment: Energy-balance model, CO₂ 280→560 ppm, ice-albedo feedback on: warming 1.13 K (baseline 288.7 K).
- Experiment: Started from a frozen Earth (230 K) the model returns to 289.8 K: no second stable climate in this model at today's sunlight.

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.

## Room-temperature superconductivity

> What sets the temperature at which a material becomes superconducting, and what energy scales would allow it at room temperature?

*Euresis approached it through:* Landauer limit, Mean kinetic energy of a gas molecule, Helmholtz free energy, Boltzmann factor, Equipartition theorem (per quadratic degree of freedom), Standard Gibbs energy and equilibrium

- Scale: temperature ~ k_B^4/(sqrt(G)*hbar^(13/4)*sigma^(5/4)) ≈ 1.352e+33 (SI)
- Scale: temperature ~ c^(13/6)/(sqrt(G)*k_B^(1/3)*sigma^(1/6)) ≈ 1.914e+32 (SI)
- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*k_B) ≈ 1.417e+32 (SI)
- Scale: temperature ~ c^2/(sqrt(G)*hbar^(1/4)*sigma^(1/4)) ≈ 2.225e+32 (SI)
- Scale: temperature ~ energy/k_B
- Scale: temperature ~ energy^(4/5)/(G^(1/10)*hbar^(13/20)*sigma^(1/4))
- Dimensionless number: G*T_CMB^2*k_B^2/(c^5*hbar) ≈ 3.701e-64
- Dimensionless number: G^2*T_CMB^4*hbar*sigma/c^8 ≈ 2.253e-128
- Composition: H = T_temperature*(-R*log(K_equilibrium) + S)  [candidate (not in knowledge base, untested); via Standard Gibbs energy and equilibrium → Gibbs free energy]
- Composition: A_helmholtz = dU*(-2*S_entropy + k_B)/k_B  [candidate (not in knowledge base, untested); via Helmholtz free energy → Equipartition theorem (per quadratic degree of freedom)]
- Composition: A_helmholtz = dU*k_B/(2*S_entropy + k_B)  [candidate (not in knowledge base, untested); via Helmholtz free energy → Equipartition theorem (per quadratic degree of freedom)]
- Analogy: F = m*v/t  [candidate (not in knowledge base, untested); via Energy stored in an inductor → Kinetic energy → Self-induced EMF]
- Composition: G_gibbs = H*R*log(K_equilibrium)/(R*log(K_equilibrium) - S)  [candidate (not in knowledge base, untested); via Standard Gibbs energy and equilibrium → Gibbs free energy]
- Composition: A_helmholtz = -E*S_entropy/(k_B*log(2)) + E  [candidate (not in knowledge base, untested); via Landauer limit → Helmholtz free energy]

**Verdict:** Quantified, not solved: Euresis derived the characteristic scales the answer must involve and connected them to known laws. These frame the mystery; they do not explain its mechanism.

## Limits of lifespan

> Why do larger animals live longer while their hearts beat a similar total number of times, and what links metabolic rate, body mass and lifespan?

*Euresis approached it through:* Allometric lifespan, Kleiber's law, Reduced mass, Orbital energy, Newton's law of universal gravitation, Gravitational potential energy

- Scale: metabolic rate ~ c^5/G ≈ 3.628e+52 (SI)
- Scale: metabolic rate ~ c^2*mass/lifespan
- Scale: metabolic rate ~ G^(2/3)*mass^(5/3)/lifespan^(5/3)
- Scale: metabolic rate ~ c^4*mass^2/h
- Scale: metabolic rate ~ G^4*mass^10/h^5
- Scale: metabolic rate ~ h/lifespan^2
- Analogy: r_H = 3^(2/3)*a_semi/3  [candidate (not in knowledge base, untested); via Reduced mass → Resistors in parallel → Hill sphere radius]
- Analogy: gravitational_potential = G*m/r_distance  [candidate (not in knowledge base, untested); via Coulomb's law → Newton's law of universal gravitation → Potential of a point charge]
- Analogy: E_electric = 2*L_length*k_e*q/r_distance^3  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Coulomb's law → Tidal acceleration]
- Analogy: E = -k_e*q1*q2/(2*a_semi)  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Coulomb's law → Orbital energy]
- Composition: U = -G*m1*m2/√(G*m1*m2/F)  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Gravitational potential energy]
- Composition: F = 4*E^2/(G*m1*m2)  [candidate (not in knowledge base, untested); via Orbital energy → Newton's law of universal gravitation]

**Verdict:** Quantified, not solved: Euresis derived the characteristic scales the answer must involve and connected them to known laws. These frame the mystery; they do not explain its mechanism.

## Origin of life

> How could a population of self-replicating molecules grow from rare chemical reactions, given reaction rates, activation energy and temperature?

*Euresis approached it through:* Exponential population growth, RMS speed of gas molecules, Lotka-Volterra prey equation, Eyring equation, Logistic growth rate, Arrhenius equation

- Scale: activation energy (per mole) ~ R*temperature
- Composition: dNdt = b_predation*y*(K_carrying - N_population)  [candidate (not in knowledge base, untested); via Lotka-Volterra prey equation → Logistic growth rate]
- Composition: dNdt = K_carrying*b_predation*y*(-b_predation*y + r_growth)/r_growth  [candidate (not in knowledge base, untested); via Lotka-Volterra prey equation → Logistic growth rate]
- Composition: K = 3*Ea*k_B/(2*R*log(A_pre/k_rate))  [candidate (not in knowledge base, untested); via Arrhenius equation → Mean kinetic energy of a gas molecule]
- Composition: mf = -3*T_temperature*k_B/(2*c^2) + m0  [candidate (not in knowledge base, untested); via Reaction Q-value → Mean kinetic energy of a gas molecule]
- Composition: dNdt = N0_initial*(-b_predation*y + r_growth)*exp(r_growth*t)  [candidate (not in knowledge base, untested); via Exponential population growth → Lotka-Volterra prey equation]
- Composition: p_probability = exp(c^2*(-m0 + mf)/(T_temperature*k_B))  [candidate (not in knowledge base, untested); via Reaction Q-value → Boltzmann factor]
- Experiment: Arrhenius, Ea = 50 kJ/mol: rate rises ×367 from 0 °C to 100 °C.
- Experiment: Arrhenius, Ea = 100 kJ/mol: rate rises ×1.35e+05 from 0 °C to 100 °C.
- Experiment: Autocatalysis A + R → 2R with decay R → D, starting from one replicator per million: R grows to 0.316 mol/L — exponential take-off once copying outpaces decay.

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.

## Turbulence

> When does smooth fluid flow become turbulent, and which dimensionless combination of velocity, viscosity, density and size controls it?

*Euresis approached it through:* Mass flow rate, Kinematic viscosity, Continuity (flow rate), Poiseuille's law, Stokes terminal velocity, Darcy's law

- Analogy: d_roche = 2^(1/3)*r  [candidate (not in knowledge base, untested); via Bernoulli dynamic pressure → Kinetic energy → Roche limit (rigid body)]
- Analogy: P_pressure = rho_density*v^2  [candidate (not in knowledge base, untested); via Moment of inertia of a solid disk → Bernoulli dynamic pressure → Moment of inertia of a point mass]
- Analogy: P_pressure = 2*rho_density*v^2/5  [candidate (not in knowledge base, untested); via Moment of inertia of a solid disk → Bernoulli dynamic pressure → Moment of inertia of a solid sphere]
- Analogy: k_wavenumber = L_length/A  [candidate (not in knowledge base, untested); via Reynolds number → Fourier's law of conduction → Kinematic viscosity]
- Composition: F_thrust = mdot^2/(A*rho_density)  [candidate (not in knowledge base, untested); via Mass flow rate → Rocket thrust]
- Composition: F_thrust = A*rho_density*v^2  [candidate (not in knowledge base, untested); via Mass flow rate → Rocket thrust]
- Experiment: Reynolds number for a 1 m pipe flow of water at 1 m/s: Re = ρvL/η ≈ 1e+06 (turbulent above ≈ 2300–4000, the empirical transition).

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.
