# Mysteries posed to Euresis

The mysteries (questions only) were written by a person; everything below was produced by Euresis from its own knowledge base, reasoning engines, simulators and data analysis. Literature novelty checks could not run in this environment (no network access to paper databases).

## Hot-Jupiter radius anomaly

> Why are many giant planets orbiting close to their stars larger in radius than cooling models predict, and what law links their radius to the stellar flux they receive and their mass?

*Euresis approached it through:* Cyclotron radius, Nuclear radius, Stellar luminosity, Law of Laplace (blood vessel), Schwarzschild radius, Photon sphere radius

- Scale: radius ~ sqrt(G)*sqrt(hbar)/c^(3/2) ≈ 1.616e-35 (SI)
- Scale: radius ~ sqrt(G)*e/(c^2*sqrt(epsilon_0)) ≈ 4.894e-36 (SI)
- Scale: radius ~ sqrt(G)*epsilon_0^(3/2)*hbar^2/e^3 ≈ 5.820e-34 (SI)
- Dimensionless number: a_0/R_earth ≈ 8.297e-18
- Dimensionless number: R_earth^2*c^4*epsilon_0/(G*e^2) ≈ 1.698e+84
- Dimensionless number: G*hbar/(R_earth^2*c^3) ≈ 6.421e-84
- Composition: L_luminosity = c^12*ħ^4*r^2*σ/(1024*π^3*G^4*k_B^4*m^4)  [candidate (not in knowledge base, untested); via Stellar luminosity → Hawking temperature of a black hole]
- Composition: F_flux = T_temperature^4*σ  [candidate (not in knowledge base, untested); via Stellar luminosity → Flux from luminosity]
- Interpretation: radiant flux density ∝ temperature^4, whatever the power.
- Composition: T_temperature = c*ħ/(4*π*k_B*r_schwarzschild)  [candidate (not in knowledge base, untested); via Schwarzschild radius → Hawking temperature of a black hole]
- Interpretation: temperature × Schwarzschild radius is the same for every mass: the mass cancels out.
- Composition: T_temperature = 3*c*ħ/(8*π*k_B*r_photon)  [candidate (not in knowledge base, untested); via Photon sphere radius → Hawking temperature of a black hole]
- Interpretation: temperature × photon sphere radius is the same for every mass: the mass cancels out.
- Composition: T_w = P_pressure*m*v/(B*q)  [candidate (not in knowledge base, untested); via Cyclotron radius → Law of Laplace (blood vessel)]
- Composition: T_w = 2*G*P_pressure*m/c^2  [candidate (not in knowledge base, untested); via Law of Laplace (blood vessel) → Schwarzschild radius]
- Composition: T_w = 3*G*P_pressure*m/c^2  [candidate (not in knowledge base, untested); via Law of Laplace (blood vessel) → Photon sphere radius]
- Composition: m = A_mass^(1/3)*c^2*r_0/(2*G)  [candidate (not in knowledge base, untested); via Nuclear radius → Schwarzschild radius]
- Interpretation: mass ∝ mass number^1/3, whatever the distance / separation.
- Data: Searched 18 candidate laws on 620 real giant planets (Open Exoplanet Catalogue).
- Data: Best law (BIC): Euresis: R = [a·x^p·exp(b·x^r)](F) · M^c — cross-validated error 0.0989 dex vs 0.1117 dex for a simple power law in mass and flux.
- Data: Radius rises with flux but saturates and turns over at the highest flux (parameters 0.962, -0.0402, 0.0614, 0.315, -0.0473).
- Data: Unexplained residual correlates with host-star metallicity (ρ = -0.145): metal-rich systems host denser giant planets.

**Verdict:** Partial progress: found a better-fitting empirical law in real data and a residual trend; the physical mechanism remains unexplained. Literature novelty unchecked.

## Why is gravity so weak?

> Why is the gravitational force between elementary particles so much weaker than the electromagnetic force, and what sets the ratio of the Planck mass to the proton mass?

*Euresis approached it through:* Centripetal force, Newton's second law, Chandrasekhar limit, Lorentz force (magnetic, perpendicular), Kinetic friction, Archimedes' principle

- Dimensionless number: G*m_p^2/(c*hbar) ≈ 5.906e-39
- Composition: F_centripetal = m*v^4/(G*m1)  [candidate (not in knowledge base, untested); via Centripetal force → Newton's law of universal gravitation]
- Composition: F_centripetal = B^2*q^2*r/m  [candidate (not in knowledge base, untested); via Centripetal force → Lorentz force (magnetic, perpendicular)]
- Composition: F_centripetal = m*v^4/(G*m2)  [candidate (not in knowledge base, untested); via Centripetal force → Newton's law of universal gravitation]
- Composition: F = 0.774402486238505*a*(c*ħ/G)^(3/2)/m_p^2  [candidate (not in knowledge base, untested); via Newton's second law → Chandrasekhar limit]
- Interpretation: force ∝ acceleration^1, whatever the mass.
- Composition: rho_density = m*v^2/(V*g*r)  [candidate (not in knowledge base, untested); via Centripetal force → Archimedes' principle]
- Composition: F_centripetal = 0.774402486238505*v^2*(c*ħ/G)^(3/2)/(m_p^2*r)  [candidate (not in knowledge base, untested); via Centripetal force → Chandrasekhar limit]
- Composition: I_current = m*v^2/(B*L_length*r)  [candidate (not in knowledge base, untested); via Centripetal force → Force on a current-carrying wire]
- Composition: a = B*q*v/m  [candidate (not in knowledge base, untested); via Newton's second law → Lorentz force (magnetic, perpendicular)]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Scale of quantum gravity

> At what length, energy, time and temperature must gravity and quantum mechanics merge, and which physical systems come closest to that regime?

*Euresis approached it through:* Particle in a box energy levels, Energy-time uncertainty, Mean kinetic energy of a gas molecule, Diffusion time, Thermal diffusion time, Quantum harmonic oscillator levels

- Scale: temperature ~ energy/k_B
- Scale: temperature ~ h/(k_B*time)
- Scale: temperature ~ hbar/(k_B*time)
- Dimensionless number: hbar/h ≈ 0.159
- Composition: E_energy = h*n_quantum*v/(4*L_length)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Kinetic energy]
- Analogy: v = K/(L_length*f_c*m)  [candidate (not in knowledge base, untested); via Bernoulli dynamic pressure → Kinetic energy → Geostrophic wind]
- Composition: t = h^2*n_quantum^2/(16*D*E_energy*m)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Diffusion time]
- Composition: t = h^2*n_quantum^2/(8*E_energy*alpha_d*m)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Thermal diffusion time]
- Composition: L_length = √(3)*h*n_quantum*√(1/(T_temperature*k_B*m))/6  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Mean kinetic energy of a gas molecule]
- Composition: tau_time = h^2*n_quantum^2/(4*E_energy*L_length^2*b_damπng)  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Damped oscillator decay time]
- Analogy: F = m*v/t  [candidate (not in knowledge base, untested); via Energy stored in an inductor → Kinetic energy → Self-induced EMF]
- Composition: p_probability = exp(-h^2*n_quantum^2/(8*L_length^2*T_temperature*k_B*m))  [candidate (not in knowledge base, untested); via Particle in a box energy levels → Boltzmann factor]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Black hole information

> How much information can a black hole hold, how hot is it, and how long does it take to evaporate, given its entropy and Hawking temperature?

*Euresis approached it through:* Hawking temperature of a black hole, Bekenstein-Hawking entropy, Binary entropy function, Clausius entropy, Shannon information of an outcome, Boltzmann entropy

- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*k_B) ≈ 1.417e+32 (SI)
- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*entropy)
- Composition: I_information = 2*π*T_temperature*k_B*r/(c*ħ)  [candidate (not in knowledge base, untested); via Landauer limit → Bekenstein bound]
- Composition: I_information = 2*π*T_temperature*dS*r/(c*ħ*log(2))  [candidate (not in knowledge base, untested); via Clausius entropy → Bekenstein bound]
- Composition: E = c^3*ħ*log(2)/(8*π*G*m)  [candidate (not in knowledge base, untested); via Hawking temperature of a black hole → Landauer limit]
- Interpretation: mass × energy is the same for every temperature: the temperature cancels out.
- Composition: n_amount = Q/(R*T_temperature*(-x*log(x) + x*log(1 - x) - log(1 - x)))  [candidate (not in knowledge base, untested); via Clausius entropy → Ideal entropy of mixing (binary)]
- Composition: dS = 8*π*G*Q*k_B*m/(c^3*ħ)  [candidate (not in knowledge base, untested); via Hawking temperature of a black hole → Clausius entropy]
- Composition: E = -c*ħ*log(p_probability)/(2*π*r)  [candidate (not in knowledge base, untested); via Shannon information of an outcome → Bekenstein bound]
- Composition: A = 4*G*ħ*log(N_number)/c^3  [candidate (not in knowledge base, untested); via Bekenstein-Hawking entropy → Boltzmann entropy]

**Verdict:** Quantified, not solved: Euresis derived the characteristic scales the answer must involve and connected them to known laws. These frame the mystery; they do not explain its mechanism.

## Dark matter in galaxies

> Why do stars in the outer parts of galaxies orbit faster than the visible mass and gravity predict, and what density of unseen matter would explain flat rotation velocity?

*Euresis approached it through:* Density, Mass flow rate, Cyclotron radius, Orbital period of a circular orbit, Surface gravity, Innermost stable circular orbit

- Scale: velocity ~ sqrt(G)*density^(1/6)*mass^(1/3)
- Dimensionless number: g_n/(Omega_E*c) ≈ 4.486e-04
- Dimensionless number: G*Omega_E^2*hbar/c^5 ≈ 1.546e-95
- Composition: T = 12*π*G*m/(c^2*v_orbital)  [candidate (not in knowledge base, untested); via Orbital period of a circular orbit → Innermost stable circular orbit]
- Composition: r = V*rho_density*v/(B*q)  [candidate (not in knowledge base, untested); via Density → Cyclotron radius]
- Composition: v_orbital = √(G*V*rho_density/r)  [candidate (not in knowledge base, untested); via Density → Circular orbital velocity]
- Composition: v_orbital = 2^(1/3)*π^(1/3)*(G*m/T)^(1/3)  [candidate (not in knowledge base, untested); via Orbital period of a circular orbit → Circular orbital velocity]
- Composition: mdot = A*rho_density*√(G*m/r)  [candidate (not in knowledge base, untested); via Mass flow rate → Circular orbital velocity]
- Composition: g = 4*π^2*G*m/(T^2*v_orbital^2)  [candidate (not in knowledge base, untested); via Orbital period of a circular orbit → Surface gravity]
- Composition: mdot = A*m*v/V  [candidate (not in knowledge base, untested); via Density → Mass flow rate]
- Composition: r = m*mdot/(A*B*q*rho_density)  [candidate (not in knowledge base, untested); via Mass flow rate → Cyclotron radius]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Dark energy and the cosmological constant

> What energy density does the expansion rate of the universe imply, and how does it compare with the vacuum energy density at the Planck scale?

*Euresis approached it through:* Fermi energy of a free electron gas, Energy density of magnetic field, Margolus-Levitin bound, Energy density of electric field, Elastic energy density, Photon energy from wavelength

- Scale: energy density ~ density/(epsilon_0*mu_0)
- Dimensionless number: hbar/h ≈ 0.159
- Dimensionless number: G*m_e^2/(c*h) ≈ 2.788e-46
- Dimensionless number: c^2*epsilon_0*mu_0 ≈ 1
- Composition: E = π*c^2*ħ*m/(2*h)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Bremermann's limit]
- Interpretation: mass ∝ energy^1, whatever the computation rate (operations/s).
- Composition: E_rest = h*rate  [candidate (not in knowledge base, untested); via Bremermann's limit → Mass-energy equivalence]
- Interpretation: computation rate (operations/s) ∝ rest energy^1, whatever the mass.
- Composition: rate = 2*c^2*m/(π*ħ)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Mass-energy equivalence]
- Interpretation: computation rate (operations/s) ∝ mass^1, whatever the energy.
- Composition: E_electric = B*√(1/(ε₀*μ₀))  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Energy density of electric field]
- Interpretation: electric field ∝ magnetic flux density^1, whatever the energy density.
- Composition: f_frequency = c^2*m/h  [candidate (not in knowledge base, untested); via Planck-Einstein relation → Mass-energy equivalence]
- Interpretation: mass ∝ frequency^1, whatever the energy.
- Composition: rate = 2*f_frequency*h/(π*ħ)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Planck-Einstein relation]
- Interpretation: computation rate (operations/s) ∝ frequency^1, whatever the energy.
- Composition: rate = 2*c*h/(π*ħ*lam)  [candidate (not in knowledge base, untested); via Margolus-Levitin bound → Photon energy from wavelength]
- Interpretation: computation rate (operations/s) × wavelength is the same for every energy: the energy cancels out.
- Composition: B = σ_s*√(μ₀/Y)  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Elastic energy density]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Solar coronal heating

> Why is the solar corona millions of kelvin hotter than the surface, and could magnetic energy density in the solar atmosphere supply the heat?

*Euresis approached it through:* Mass-luminosity relation (main sequence), Solar constant, Energy density of magnetic field, Magnetic dipole energy, Magnetic flux, Magnetic pressure

- Dimensionless number: R_sun/AU ≈ 0.00465
- Dimensionless number: L_sun*yr^3/(AU^2*M_sun) ≈ 2.703e-04
- Composition: U = √(2)*mu_magnetic*√(μ₀*u_energy)  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Magnetic dipole energy]
- Composition: P_pressure = u_energy  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Magnetic pressure]
- Interpretation: pressure ∝ energy density^1, whatever the magnetic flux density.
- Composition: Phi_magnetic = A*U/mu_magnetic  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Magnetic flux]
- Composition: Q = 10000*M_sun*c_specific*dT*(yr/t_stellar)^(2/5)  [candidate (not in knowledge base, untested); via Main-sequence lifetime → Specific heat]
- Composition: P_pressure = U^2/(2*μ₀*mu_magnetic^2)  [candidate (not in knowledge base, untested); via Magnetic dipole energy → Magnetic pressure]
- Composition: t_stellar = 10000000000*yr/(Q/(L_latent*M_sun))^(5/2)  [candidate (not in knowledge base, untested); via Latent heat → Main-sequence lifetime]
- Composition: L_latent = c_specific*dT  [candidate (not in knowledge base, untested); via Latent heat → Specific heat]
- Composition: Phi_magnetic = √(2)*A*√(μ₀*u_energy)  [candidate (not in knowledge base, untested); via Energy density of magnetic field → Magnetic flux]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Climate sensitivity

> How much does Earth's surface temperature rise for a doubling of carbon dioxide, and how much do feedbacks such as ice albedo amplify it?

*Euresis approached it through:* Planetary equilibrium temperature, Capillary rise (Jurin's law), Doubling time, Young-Laplace (sphere), Mean free path from cross-section, Osmotic pressure (van 't Hoff)

- Dimensionless number: a_s/(M_earth*Omega_E^2*R_earth^2) ≈ 2.208e-42
- Dimensionless number: M_earth^3*Omega_E^5*R_earth^8*sigma/k_B^4 ≈ 1.877e+192
- Analogy: dF = C_co2*a_F  [candidate (not in knowledge base, untested); via Tsiolkovsky rocket equation → CO2 radiative forcing → Momentum]
- Analogy: d_roche = 2^(1/3)*r  [candidate (not in knowledge base, untested); via Speed of sound in a solid rod → Neuronal length constant (cable theory) → Roche limit (rigid body)]
- Composition: σ_x = √(2)*π*P_pressure*d_molecular^2/(T_temperature*k_B*n_number)  [candidate (not in knowledge base, untested); via Mean free path from cross-section → Mean free path of a gas]
- Composition: lam_mean = √(2)*T_temperature*k_B*r/(4*π*d_molecular^2*gamma_s)  [candidate (not in knowledge base, untested); via Young-Laplace (sphere) → Mean free path of a gas]
- Composition: K = 3*√(2)*k_B*(F_flux*(1 - A_albedo)/(e_emissivity*σ))^(1/4)/4  [candidate (not in knowledge base, untested); via Planetary equilibrium temperature → Mean kinetic energy of a gas molecule]
- Composition: lam_mean = k_B*(F_flux*(1 - A_albedo)/(e_emissivity*σ))^(1/4)/(2*π*P_pressure*d_molecular^2)  [candidate (not in knowledge base, untested); via Planetary equilibrium temperature → Mean free path of a gas]
- Composition: Pi = √(2)*R*c_concentration*i*(F_flux*(1 - A_albedo)/(e_emissivity*σ))^(1/4)/2  [candidate (not in knowledge base, untested); via Planetary equilibrium temperature → Osmotic pressure (van 't Hoff)]
- Composition: P_pressure = g*h_height*rho_density/cos(theta)  [candidate (not in knowledge base, untested); via Capillary rise (Jurin's law) → Young-Laplace (sphere)]
- Experiment: Energy-balance model, CO₂ 280→560 ppm, ice-albedo feedback off: warming 1.11 K (baseline 287.8 K).
- Experiment: Energy-balance model, CO₂ 280→560 ppm, ice-albedo feedback on: warming 1.13 K (baseline 288.7 K).
- Experiment: Started from a frozen Earth (230 K) the model returns to 289.8 K: no second stable climate in this model at today's sunlight.

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.

## Room-temperature superconductivity

> What sets the temperature at which a material becomes superconducting, and what energy scales would allow it at room temperature?

*Euresis approached it through:* Landauer limit, Mean kinetic energy of a gas molecule, Equipartition theorem (per quadratic degree of freedom), Hawking temperature of a black hole, Helmholtz free energy, Boltzmann factor

- Scale: temperature ~ k_B^4/(sqrt(G)*hbar^(13/4)*sigma^(5/4)) ≈ 1.352e+33 (SI)
- Scale: temperature ~ c^(13/6)/(sqrt(G)*k_B^(1/3)*sigma^(1/6)) ≈ 1.914e+32 (SI)
- Scale: temperature ~ c^(5/2)*sqrt(hbar)/(sqrt(G)*k_B) ≈ 1.417e+32 (SI)
- Scale: temperature ~ c^2/(sqrt(G)*hbar^(1/4)*sigma^(1/4)) ≈ 2.225e+32 (SI)
- Scale: temperature ~ energy/k_B
- Scale: temperature ~ energy^(4/5)/(G^(1/10)*hbar^(13/20)*sigma^(1/4))
- Dimensionless number: G*T_CMB^2*k_B^2/(c^5*hbar) ≈ 3.701e-64
- Dimensionless number: G^2*T_CMB^4*hbar*sigma/c^8 ≈ 2.253e-128
- Composition: E = c^3*ħ/(16*π*G*m)  [candidate (not in knowledge base, untested); via Equipartition theorem (per quadratic degree of freedom) → Hawking temperature of a black hole]
- Interpretation: mass × energy is the same for every temperature: the temperature cancels out.
- Composition: E = c^3*ħ*log(2)/(8*π*G*m)  [candidate (not in knowledge base, untested); via Landauer limit → Hawking temperature of a black hole]
- Interpretation: mass × energy is the same for every temperature: the temperature cancels out.
- Composition: K = 3*c^3*ħ/(16*π*G*m)  [candidate (not in knowledge base, untested); via Mean kinetic energy of a gas molecule → Hawking temperature of a black hole]
- Interpretation: mass × kinetic energy is the same for every temperature: the temperature cancels out.
- Composition: H = T_temperature*(-R*log(K_equilibrium) + S)  [candidate (not in knowledge base, untested); via Standard Gibbs energy and equilibrium → Gibbs free energy]
- Composition: G_gibbs = -2*E*R*log(K_equilibrium)/k_B  [candidate (not in knowledge base, untested); via Equipartition theorem (per quadratic degree of freedom) → Standard Gibbs energy and equilibrium]
- Interpretation: Gibbs free energy (per mole) ∝ energy^1, whatever the temperature.
- Composition: G_gibbs = -E*R*log(K_equilibrium)/(k_B*log(2))  [candidate (not in knowledge base, untested); via Landauer limit → Standard Gibbs energy and equilibrium]
- Interpretation: Gibbs free energy (per mole) ∝ energy^1, whatever the temperature.
- Composition: G_gibbs = -2*K*R*log(K_equilibrium)/(3*k_B)  [candidate (not in knowledge base, untested); via Mean kinetic energy of a gas molecule → Standard Gibbs energy and equilibrium]
- Interpretation: kinetic energy ∝ Gibbs free energy (per mole)^1, whatever the temperature.
- Composition: E = dU*k_B/(2*S_entropy + k_B)  [candidate (not in knowledge base, untested); via Equipartition theorem (per quadratic degree of freedom) → Helmholtz free energy]

**Verdict:** Quantified, not solved: Euresis derived the characteristic scales the answer must involve and connected them to known laws. These frame the mystery; they do not explain its mechanism.

## Limits of lifespan

> Why do larger animals live longer while their hearts beat a similar total number of times, and what links metabolic rate, body mass and lifespan?

*Euresis approached it through:* Allometric lifespan, Kleiber's law, Allometric heart rate, Newton's law of universal gravitation, Reduced mass, Basic reproduction number (SIR)

- Scale: metabolic rate ~ G^(2/3)*mass^(5/3)/lifespan^(5/3)
- Composition: P_metabolic = a_bmr*(t_lifespan^4/a_lifespan^4)^(3/4)  [candidate (not in knowledge base, untested); via Allometric lifespan → Kleiber's law]
- Interpretation: lifespan ∝ metabolic rate^1/3, whatever the mass.
- Composition: f_heart = a_heart/((P_metabolic/a_bmr)^(4/3))^(1/4)  [candidate (not in knowledge base, untested); via Kleiber's law → Allometric heart rate]
- Interpretation: metabolic rate ∝ heart rate^-3, whatever the mass.
- Composition: f_heart = a_heart/(t_lifespan^4/a_lifespan^4)^(1/4)  [candidate (not in knowledge base, untested); via Allometric lifespan → Allometric heart rate]
- Interpretation: lifespan × heart rate is the same for every mass: the mass cancels out.
- Analogy: r_H = 3^(2/3)*a_semi/3  [candidate (not in knowledge base, untested); via Reduced mass → Resistors in parallel → Hill sphere radius]
- Composition: U = -G*m1*m2/√(G*m1*m2/F)  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Gravitational potential energy]
- Analogy: gravitational_potential = G*m/r_distance  [candidate (not in knowledge base, untested); via Coulomb's law → Newton's law of universal gravitation → Potential of a point charge]
- Composition: E = -G*m1*m2/(2*√(G*m1*m2/F))  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Orbital energy]
- Analogy: E_electric = 2*L_length*k_e*q/r_distance^3  [candidate (not in knowledge base, untested); via Newton's law of universal gravitation → Coulomb's law → Tidal acceleration]

**Verdict:** Candidate connections only: relations not in its knowledge base, untested and unexplained.

## Origin of life

> How could a population of self-replicating molecules grow from rare chemical reactions, given reaction rates, activation energy and temperature?

*Euresis approached it through:* Eyring equation, Arrhenius equation, Exponential population growth, RMS speed of gas molecules, Lotka-Volterra prey equation, Mean kinetic energy of a gas molecule

- Scale: activation energy (per mole) ~ R*temperature
- Composition: K = 3*Ea*k_B/(2*R*log(A_pre/k_rate))  [candidate (not in knowledge base, untested); via Arrhenius equation → Mean kinetic energy of a gas molecule]
- Interpretation: activation energy (per mole) ∝ kinetic energy^1, whatever the temperature.
- Composition: Ea = R*T_temperature*log(A_pre*h*exp(G_activation/(R*T_temperature))/(T_temperature*k_B*kappa))  [candidate (not in knowledge base, untested); via Eyring equation → Arrhenius equation]
- Composition: p_probability = exp(-E*R*log(A_pre/k_rate)/(Ea*k_B))  [candidate (not in knowledge base, untested); via Arrhenius equation → Boltzmann factor]
- Composition: mf = -3*T_temperature*k_B/(2*c^2) + m0  [candidate (not in knowledge base, untested); via Mean kinetic energy of a gas molecule → Reaction Q-value]
- Composition: p_probability = exp(c^2*(-m0 + mf)/(T_temperature*k_B))  [candidate (not in knowledge base, untested); via Reaction Q-value → Boltzmann factor]
- Composition: p_probability = exp(-3*E/(m*v^2))  [candidate (not in knowledge base, untested); via RMS speed of gas molecules → Boltzmann factor]
- Composition: dNdt = b_predation*y*(K_carrying - N_population)  [candidate (not in knowledge base, untested); via Lotka-Volterra prey equation → Logistic growth rate]
- Composition: v = √(3)*√(Ea*k_B/(R*m*log(A_pre/k_rate)))  [candidate (not in knowledge base, untested); via Arrhenius equation → RMS speed of gas molecules]
- Experiment: Arrhenius, Ea = 50 kJ/mol: rate rises ×367 from 0 °C to 100 °C.
- Experiment: Arrhenius, Ea = 100 kJ/mol: rate rises ×1.35e+05 from 0 °C to 100 °C.
- Experiment: Autocatalysis A + R → 2R with decay R → D, starting from one replicator per million: R grows to 0.316 mol/L — exponential take-off once copying outpaces decay.

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.

## Turbulence

> When does smooth fluid flow become turbulent, and which dimensionless combination of velocity, viscosity, density and size controls it?

*Euresis approached it through:* Mass flow rate, Continuity (flow rate), Stokes terminal velocity, Density, Kinematic viscosity, Poiseuille's law

- Composition: F_drag = 6*π*nu*r*rho_density*v  [candidate (not in knowledge base, untested); via Kinematic viscosity → Stokes' law]
- Composition: Re = 6*π*L_length*r*rho_density*v^2/F_drag  [candidate (not in knowledge base, untested); via Stokes' law → Reynolds number]
- Composition: Re = π*P_pressure*r^4*rho_density*v/(8*Q_flow*eta_viscosity^2)  [candidate (not in knowledge base, untested); via Poiseuille's law → Reynolds number]
- Composition: Q_flow = P_pressure*k_p*mdot/(L_length*eta_viscosity*rho_density*v)  [candidate (not in knowledge base, untested); via Mass flow rate → Darcy's law]
- Composition: Re = A*P_pressure*k_p*rho_density*v/(Q_flow*eta_viscosity^2)  [candidate (not in knowledge base, untested); via Darcy's law → Reynolds number]
- Composition: nu = 2*g*r^2*(-rho_density + rho_p)/(9*rho_p*v_terminal)  [candidate (not in knowledge base, untested); via Stokes terminal velocity → Kinematic viscosity]
- Composition: nu = 2*g*r^2*(-rho_density + rho_p)/(9*rho_density*v_terminal)  [candidate (not in knowledge base, untested); via Stokes terminal velocity → Kinematic viscosity]
- Composition: Re = 8*L_length^2*Q_flow*rho_density*v/(π*P_pressure*r^4)  [candidate (not in knowledge base, untested); via Poiseuille's law → Reynolds number]
- Experiment: Reynolds number for a 1 m pipe flow of water at 1 m/s: Re = ρvL/η ≈ 1e+06 (turbulent above ≈ 2300–4000, the empirical transition).

**Verdict:** Explored by simulation: Euresis' models reproduce the known structure of the problem (magnitudes and feedbacks); the open part needs physics its models do not contain.
