"""Fundamental formulas of science.

Each line:  domain | name | equation (SymPy syntax) | symbol:quantity_id ...
Symbols that are keys of CONSTANTS (c, h, G, k_B ...) and `pi` need no mapping.
Every formula is checked for dimensional consistency at load time.
"""

_FORMULAS = r"""
# ---------------------------------------------------------------- mechanics
mechanics | Newton's second law | F = m*a | F:force m:mass a:acceleration
mechanics | Weight | W = m*g | W:weight m:mass g:gravitational_acceleration
mechanics | Momentum | p = m*v | p:momentum m:mass v:velocity
mechanics | Impulse-momentum theorem | J = F*t | J:impulse F:force t:time
mechanics | Kinetic energy | K = m*v**2/2 | K:kinetic_energy m:mass v:velocity
mechanics | Gravitational potential energy near Earth | U = m*g*h_ | U:potential_energy m:mass g:gravitational_acceleration h_:height
mechanics | Work | W = F*d | W:work F:force d:displacement
mechanics | Power | P = W/t | P:power W:work t:time
mechanics | Mechanical power | P = F*v | P:power F:force v:velocity
mechanics | Hooke's law | F = k*x | F:force k:spring_constant x:displacement
mechanics | Elastic potential energy | U = k*x**2/2 | U:potential_energy k:spring_constant x:displacement
mechanics | Kinematics: velocity | v = v0 + a*t | v:final_velocity v0:initial_velocity a:acceleration t:time
mechanics | Kinematics: position | s = v0*t + a*t**2/2 | s:displacement v0:initial_velocity a:acceleration t:time
mechanics | Kinematics: timeless | v**2 = v0**2 + 2*a*s | v:final_velocity v0:initial_velocity a:acceleration s:displacement
mechanics | Kinetic friction | f = mu*N | f:friction_force mu:friction_coefficient N:normal_force
mechanics | Centripetal acceleration | a = v**2/r | a:centripetal_acceleration v:velocity r:radius
mechanics | Angular velocity and speed | v = omega*r | v:velocity omega:angular_velocity r:radius
mechanics | Angular frequency | omega = 2*pi*f | omega:angular_frequency f:frequency
mechanics | Period and frequency | T = 1/f | T:period f:frequency
mechanics | Torque | tau = r*F*sin(theta) | tau:torque r:radius F:force theta:angle
mechanics | Rotational second law | tau = I*alpha_ | tau:torque I:moment_of_inertia alpha_:angular_acceleration
mechanics | Angular momentum | L = I*omega | L:angular_momentum I:moment_of_inertia omega:angular_velocity
mechanics | Rotational kinetic energy | K = I*omega**2/2 | K:kinetic_energy I:moment_of_inertia omega:angular_velocity
mechanics | Moment of inertia of a point mass | I = m*r**2 | I:moment_of_inertia m:mass r:radius
mechanics | Mass-spring oscillator period | T = 2*pi*sqrt(m/k) | T:period m:mass k:spring_constant
mechanics | Simple pendulum period | T = 2*pi*sqrt(L/g) | T:period L:length g:gravitational_acceleration
mechanics | Work-energy theorem | W = K | W:work K:kinetic_energy
# -------------------------------------------------------------- gravitation
gravitation | Newton's law of universal gravitation | F = G*m1*m2/r**2 | F:force m1:mass1 m2:mass2 r:distance
gravitation | Gravitational potential energy | U = -G*m1*m2/r | U:potential_energy m1:mass1 m2:mass2 r:distance
gravitation | Surface gravity | g = G*M/r**2 | g:gravitational_acceleration M:mass r:radius
gravitation | Escape velocity | v = sqrt(2*G*M/r) | v:escape_velocity M:mass r:radius
gravitation | Circular orbital velocity | v = sqrt(G*M/r) | v:orbital_velocity M:mass r:radius
gravitation | Kepler's third law | T**2 = 4*pi**2*a**3/(G*M) | T:period a:semi_major_axis M:mass
gravitation | Schwarzschild radius | r = 2*G*M/c**2 | r:schwarzschild_radius M:mass
# ------------------------------------------------------------ waves/optics
waves | Wave equation (speed) | v = f*lam | v:wave_speed f:frequency lam:wavelength
waves | Speed of a wave on a string | v = sqrt(T_/mu_) | v:wave_speed T_:tension mu_:linear_density
waves | Speed of sound in an ideal gas | v = sqrt(gamma_*R*T/M) | v:speed_of_sound gamma_:heat_capacity_ratio T:temperature M:molar_mass
waves | Wave intensity | I = P/A | I:intensity P:power A:area
waves | Inverse-square intensity | I = P/(4*pi*r**2) | I:intensity P:power r:distance
optics | Refractive index | n = c/v | n:refractive_index v:wave_speed
optics | Snell's law | n1*sin(t1) = n2*sin(t2) | n1:refractive_index1 n2:refractive_index2 t1:angle1 t2:angle2
optics | Thin lens equation | 1/f = 1/d_o + 1/d_i | f:focal_length d_o:object_distance d_i:image_distance
optics | Magnification | m = -d_i/d_o | m:magnification d_i:image_distance d_o:object_distance
optics | Double-slit maxima | d*sin(theta) = m*lam | d:slit_separation theta:angle m:order lam:wavelength
optics | Light dispersion relation | c = f*lam | f:frequency lam:wavelength
# ---------------------------------------------------------- thermodynamics
thermodynamics | First law of thermodynamics | dU = Q - W | dU:internal_energy Q:heat W:work
thermodynamics | Ideal gas law | P*V = n*R*T | P:pressure V:volume n:amount T:temperature
thermodynamics | Ideal gas law (molecular) | P*V = N*k_B*T | P:pressure V:volume N:number T:temperature
thermodynamics | Specific heat | Q = m*c_*dT | Q:heat m:mass c_:specific_heat dT:temperature_change
thermodynamics | Heat capacity | Q = C*dT | Q:heat C:heat_capacity dT:temperature_change
thermodynamics | Latent heat | Q = m*L | Q:heat m:mass L:latent_heat
thermodynamics | Clausius entropy | dS = Q/T | dS:entropy_change Q:heat T:temperature
thermodynamics | Carnot efficiency | eta = 1 - Tc/Th | eta:efficiency Tc:temperature_cold Th:temperature_hot
thermodynamics | Engine efficiency | eta = W/Q | eta:efficiency W:work Q:heat
thermodynamics | Fourier's law of conduction | P = k*A*dT/L | P:heat_flow k:thermal_conductivity A:area dT:temperature_change L:length
thermodynamics | Stefan-Boltzmann law | P = e_*sigma*A*T**4 | P:power e_:emissivity A:area T:temperature
thermodynamics | Wien's displacement law | lam = b_W/T | lam:peak_wavelength T:temperature
thermodynamics | Isothermal work of an ideal gas | W = n*R*T*log(V2/V1) | W:work n:amount T:temperature V2:volume V1:volume
thermodynamics | Gibbs free energy | G_ = H - T*S | G_:gibbs_energy H:enthalpy T:temperature S:molar_entropy
statistical_mechanics | Boltzmann entropy | S = k_B*log(Omega) | S:entropy Omega:number
statistical_mechanics | Mean kinetic energy of a gas molecule | K = 3*k_B*T/2 | K:kinetic_energy T:temperature
statistical_mechanics | RMS speed of gas molecules | v = sqrt(3*k_B*T/m) | v:velocity T:temperature m:mass
statistical_mechanics | Boltzmann factor | p = exp(-E/(k_B*T)) | p:probability E:energy T:temperature
statistical_mechanics | Einstein-Smoluchowski diffusion | D_ = k_B*T/(6*pi*eta_*r) | D_:diffusion_coefficient T:temperature eta_:viscosity r:radius
statistical_mechanics | Mean squared displacement (3D) | x2 = 6*D_*t | x2:mean_squared_displacement D_:diffusion_coefficient t:time
statistical_mechanics | Gas constant relation | R = N_A*k_B |
# --------------------------------------------------------- electromagnetism
electromagnetism | Coulomb's law | F = k_e*q1*q2/r**2 | F:force q1:charge1 q2:charge2 r:distance
electromagnetism | Electric potential energy | U = k_e*q1*q2/r | U:potential_energy q1:charge1 q2:charge2 r:distance
electromagnetism | Coulomb constant | k_e = 1/(4*pi*epsilon_0) |
electromagnetism | Electric field definition | E = F/q | E:electric_field F:force q:charge
electromagnetism | Field of a point charge | E = k_e*q/r**2 | E:electric_field q:charge r:distance
electromagnetism | Potential of a point charge | V = k_e*q/r | V:electric_potential q:charge r:distance
electromagnetism | Potential energy of a charge | U = q*V | U:potential_energy q:charge V:voltage
electromagnetism | Uniform field and voltage | E = V/d | E:electric_field V:voltage d:distance
electromagnetism | Gauss's law (integral) | Phi = Q/epsilon_0 | Phi:electric_flux Q:charge
electromagnetism | Lorentz force (magnetic, perpendicular) | F = q*v*B | F:force q:charge v:velocity B:magnetic_field
electromagnetism | Force on a current-carrying wire | F = B*I*L | F:force B:magnetic_field I:current L:length
electromagnetism | Field of a long straight wire | B = mu_0*I/(2*pi*r) | B:magnetic_field I:current r:distance
electromagnetism | Field inside a solenoid | B = mu_0*n_*I | B:magnetic_field n_:turns_per_length I:current
electromagnetism | Magnetic flux | Phi = B*A | Phi:magnetic_flux B:magnetic_field A:area
electromagnetism | Faraday's law (EMF magnitude) | emf = N*Phi/t | emf:emf N:turns Phi:magnetic_flux t:time
electromagnetism | Cyclotron radius | r = m*v/(q*B) | r:radius m:mass v:velocity q:charge B:magnetic_field
electromagnetism | Speed of light from vacuum constants | c = 1/sqrt(mu_0*epsilon_0) |
electromagnetism | Energy density of electric field | u = epsilon_0*E**2/2 | u:energy_density E:electric_field
electromagnetism | Energy density of magnetic field | u = B**2/(2*mu_0) | u:energy_density B:magnetic_field
electromagnetism | Electromagnetic wave field ratio | E = c*B | E:electric_field B:magnetic_field
circuits | Ohm's law | V = I*R_ | V:voltage I:current R_:resistance
circuits | Electric power | P = I*V | P:power I:current V:voltage
circuits | Joule heating | P = I**2*R_ | P:power I:current R_:resistance
circuits | Resistance from resistivity | R_ = rho*L/A | R_:resistance rho:resistivity L:length A:area
circuits | Conductance | G_ = 1/R_ | G_:conductance R_:resistance
circuits | Current definition | I = q/t | I:current q:charge t:time
circuits | Capacitance | C = q/V | C:capacitance q:charge V:voltage
circuits | Parallel-plate capacitor | C = epsilon_r*epsilon_0*A/d | C:capacitance epsilon_r:relative_permittivity A:area d:distance
circuits | Energy stored in a capacitor | U = C*V**2/2 | U:energy C:capacitance V:voltage
circuits | Energy stored in an inductor | U = L*I**2/2 | U:energy L:inductance I:current
circuits | RC time constant | tau = R_*C | tau:time_constant R_:resistance C:capacitance
circuits | RL time constant | tau = L/R_ | tau:time_constant L:inductance R_:resistance
circuits | LC resonance | omega = 1/sqrt(L*C) | omega:angular_frequency L:inductance C:capacitance
circuits | Current density | J = I/A | J:current_density I:current A:area
# ---------------------------------------------------------------- fluids
fluids | Density | rho = m/V | rho:density m:mass V:volume
fluids | Pressure | P = F/A | P:pressure F:force A:area
fluids | Hydrostatic pressure | P = rho*g*h_ | P:pressure rho:density g:gravitational_acceleration h_:depth
fluids | Archimedes' principle | F = rho*V*g | F:buoyant_force rho:density V:volume g:gravitational_acceleration
fluids | Continuity (flow rate) | Q = A*v | Q:flow_rate A:area v:velocity
fluids | Bernoulli dynamic pressure | P = rho*v**2/2 | P:pressure rho:density v:velocity
fluids | Drag equation | F = rho*v**2*C_d*A/2 | F:drag_force rho:density v:velocity C_d:drag_coefficient A:area
fluids | Stokes' law | F = 6*pi*eta_*r*v | F:drag_force eta_:viscosity r:radius v:velocity
fluids | Reynolds number | Re = rho*v*L/eta_ | Re:reynolds_number rho:density v:velocity L:length eta_:viscosity
fluids | Poiseuille's law | Q = pi*r**4*P/(8*eta_*L) | Q:flow_rate r:radius P:pressure eta_:viscosity L:length
fluids | Young-Laplace (sphere) | P = 2*gamma_s/r | P:pressure gamma_s:surface_tension r:radius
materials | Stress | sigma_s = F/A | sigma_s:stress F:force A:area
materials | Young's modulus | Y = sigma_s/eps | Y:youngs_modulus sigma_s:stress eps:strain
materials | Strain | eps = dL/L | eps:strain dL:displacement L:length
# ------------------------------------------------------------ relativity
relativity | Mass-energy equivalence | E = m*c**2 | E:rest_energy m:mass
relativity | Lorentz factor | gamma_ = 1/sqrt(1 - v**2/c**2) | gamma_:lorentz_factor v:velocity
relativity | Time dilation | t = gamma_*t0 | t:time gamma_:lorentz_factor t0:proper_time
relativity | Length contraction | L = L0/gamma_ | L:length L0:proper_length gamma_:lorentz_factor
relativity | Relativistic momentum | p = gamma_*m*v | p:momentum gamma_:lorentz_factor m:mass v:velocity
relativity | Energy-momentum relation | E**2 = (p*c)**2 + (m*c**2)**2 | E:energy p:momentum m:mass
# ---------------------------------------------------------------- quantum
quantum | Planck-Einstein relation | E = h*f | E:photon_energy f:frequency
quantum | Photon momentum | p = h/lam | p:momentum lam:wavelength
quantum | de Broglie wavelength | lam = h/p | lam:de_broglie_wavelength p:momentum
quantum | Photoelectric effect | K = h*f - phi | K:kinetic_energy f:frequency phi:work_function
quantum | Heisenberg uncertainty (position-momentum) | dx*dp = hbar/2 | dx:position_uncertainty dp:momentum_uncertainty
quantum | Energy-time uncertainty | dE*dt = hbar/2 | dE:energy_uncertainty dt:time_uncertainty
quantum | Reduced Planck constant | hbar = h/(2*pi) |
quantum | Particle in a box energy levels | E = n**2*h**2/(8*m*L**2) | E:energy_level n:quantum_number m:mass L:length
quantum | Quantum harmonic oscillator levels | E = hbar*omega*(n + 1/2) | E:energy_level omega:angular_frequency n:quantum_number
quantum | Compton wavelength | lam = h/(m*c) | lam:wavelength m:mass
# ---------------------------------------------------------- atomic/nuclear
atomic | Bohr energy levels of hydrogen | E = -E_R/n**2 | E:energy_level n:quantum_number
atomic | Bohr radius | a_0 = 4*pi*epsilon_0*hbar**2/(m_e*e**2) |
atomic | Fine-structure constant | alpha = e**2/(4*pi*epsilon_0*hbar*c) |
atomic | Rydberg energy | E_R = m_e*e**4/(8*epsilon_0**2*h**2) |
nuclear | Radioactive decay law | N = N0*exp(-lam_*t) | N:number N0:initial_number lam_:decay_constant t:time
nuclear | Half-life | t_h = log(2)/lam_ | t_h:half_life lam_:decay_constant
nuclear | Mean lifetime | tau = 1/lam_ | tau:mean_lifetime lam_:decay_constant
nuclear | Activity | A = lam_*N | A:activity lam_:decay_constant N:number
nuclear | Nuclear binding energy | E = dm*c**2 | E:binding_energy dm:mass_defect
nuclear | Nuclear radius | r = r_0*A_**(1/3) | r:radius A_:mass_number
# --------------------------------------------------- astrophysics/cosmology
astrophysics | Hubble-Lemaitre law | v = H*d | v:recession_velocity H:hubble_constant d:distance
astrophysics | Redshift (low velocity) | z = v/c | z:redshift v:recession_velocity
astrophysics | Stellar luminosity | L = 4*pi*R**2*sigma*T**4 | L:luminosity R:radius T:temperature
astrophysics | Flux from luminosity | F = L/(4*pi*d**2) | F:flux L:luminosity d:distance
astrophysics | Distance modulus | m - M = 5*log(d)/log(10) - 5 | m:magnitude M:absolute_magnitude d:distance_parsec
astrophysics | Parallax distance | d = 1/p | d:distance_parsec p:parallax_arcsec
astrophysics | Hubble time | t = 1/H | t:time H:hubble_constant
# --------------------------------------------------------------- chemistry
chemistry | Moles from mass | n = m/M | n:amount m:mass M:molar_mass
chemistry | Number of particles | N = n*N_A | N:number n:amount
chemistry | Molarity | c = n/V | c:concentration n:amount V:volume
chemistry | Boyle's law (isothermal) | P1*V1 = P2*V2 | P1:pressure V1:volume P2:pressure V2:volume
chemistry | Dalton partial pressure | p_i = x*P | p_i:partial_pressure x:mole_fraction P:pressure
chemistry | Raoult's law | p_i = x*P0 | p_i:partial_pressure x:mole_fraction P0:vapor_pressure_pure
chemistry | Henry's law | c = k_H*p_i | c:concentration k_H:henry_constant p_i:partial_pressure
chemistry | pH definition | pH = -log(H_)/log(10) | pH:ph H_:hydrogen_concentration
chemistry | pOH definition | pOH = -log(OH)/log(10) | pOH:poh OH:hydroxide_concentration
chemistry | Water autoionisation | pH + pOH = 14 | pH:ph pOH:poh
chemistry | Henderson-Hasselbalch equation | pH = pKa + log(r)/log(10) | pH:ph pKa:pka r:acid_ratio
chemistry | Arrhenius equation | k = A*exp(-Ea/(R*T)) | k:rate_constant A:pre_exponential Ea:activation_energy T:temperature
chemistry | First-order integrated rate law | c = c0*exp(-k*t) | c:concentration c0:concentration k:rate_constant t:time
chemistry | First-order half-life | t_h = log(2)/k | t_h:half_life k:rate_constant
chemistry | Standard Gibbs energy and equilibrium | G_ = -R*T*log(K) | G_:gibbs_energy T:temperature K:equilibrium_constant
chemistry | Gibbs energy and cell potential | G_ = -n*F_c*E | G_:gibbs_energy n:electrons_transferred E:cell_potential
chemistry | Nernst equation | E = E0 - R*T*log(Q)/(n*F_c) | E:cell_potential E0:standard_cell_potential T:temperature Q:reaction_quotient n:electrons_transferred
chemistry | Beer-Lambert law | A = eps_*l*c | A:absorbance eps_:molar_absorptivity l:path_length c:concentration
chemistry | Osmotic pressure (van 't Hoff) | Pi = i*c*R*T | Pi:osmotic_pressure i:vant_hoff_factor c:concentration T:temperature
chemistry | Freezing point depression | dT = i*K_f*b | dT:freezing_point_depression i:vant_hoff_factor K_f:cryoscopic_constant b:molality
chemistry | Faraday's law of electrolysis | n = Q/(z*F_c) | n:amount Q:charge z:electrons_transferred
# ----------------------------------------------------------------- biology
biology | Exponential population growth | N = N0*exp(r*t) | N:population N0:initial_population r:growth_rate t:time
biology | Logistic growth rate | dNdt = r*N*(1 - N/K) | dNdt:population_rate r:growth_rate N:population K:carrying_capacity
biology | Doubling time | t_d = log(2)/r | t_d:generation_time r:growth_rate
biology | Hardy-Weinberg allele frequencies | p + q = 1 | p:allele_p q:allele_q
biology | Michaelis-Menten kinetics | v = Vmax*S/(Km + S) | v:reaction_velocity Vmax:max_velocity S:substrate_concentration Km:michaelis_constant
biology | Hill equation | theta = (L/Kd)**n/(1 + (L/Kd)**n) | theta:fraction_bound L:substrate_concentration Kd:dissociation_constant n:hill_coefficient
biology | Nernst potential of an ion | V = R*T*log(co/ci)/(z*F_c) | V:membrane_potential T:temperature co:conc_outside ci:conc_inside z:ion_charge
biology | Basic reproduction number (SIR) | R0 = beta/gamma_r | R0:basic_reproduction_number beta:transmission_rate gamma_r:recovery_rate
biology | Herd immunity threshold | H_ = 1 - 1/R0 | H_:herd_immunity_threshold R0:basic_reproduction_number
biology | Kleiber's law | P = a*M**(3/4) | P:metabolic_rate a:bmr_coefficient M:mass
biology | Breeder's equation | R_s = h2*S | R_s:response_to_selection h2:heritability S:selection_differential
# ------------------------------------------------------------- earth science
earth_science | Moment magnitude scale | Mw = 2*(log(M0)/log(10) - 9.1)/3 | Mw:moment_magnitude M0:seismic_moment_value
earth_science | Barometric formula | P = P0*exp(-h_/H_) | P:pressure P0:pressure h_:height H_:scale_height
earth_science | Atmospheric scale height | H_ = R*T/(M*g) | H_:scale_height T:temperature M:molar_mass g:gravitational_acceleration
earth_science | Dry adiabatic lapse rate | Gamma = g/c_p | Gamma:lapse_rate g:gravitational_acceleration c_p:specific_heat
# -------------------------------------------------------- information theory
information | Shannon information of an outcome | I = -log(p)/log(2) | I:information p:probability
information | Landauer limit | E = k_B*T*log(2) | E:energy T:temperature
"""

_MATH_AND_PRINCIPLES = """
mathematics | Pythagorean theorem | a² + b² = c² for a right triangle.
mathematics | Euler's identity | e^{iπ} + 1 = 0, linking analysis, algebra and geometry.
mathematics | Fundamental theorem of calculus | Differentiation and integration are inverse operations: d/dx ∫ₐˣ f(t) dt = f(x).
mathematics | Taylor series | f(x) = Σ f⁽ⁿ⁾(a)(x−a)ⁿ/n! for analytic f.
mathematics | Euler's formula | e^{iθ} = cos θ + i sin θ.
mathematics | Gaussian distribution | p(x) = exp(−(x−μ)²/2σ²)/(σ√(2π)); the central limit theorem makes it universal for sums of independent variables.
mathematics | Bayes' theorem | P(A|B) = P(B|A)P(A)/P(B): the rule for updating belief with evidence.
mathematics | Fourier transform | Any reasonable signal is a superposition of sinusoids: F(ω) = ∫ f(t) e^{−iωt} dt.
mathematics | Noether's theorem | Every differentiable symmetry of the action yields a conserved quantity (time → energy, space → momentum, rotation → angular momentum).
mathematics | Gödel's incompleteness theorems | Any consistent formal system rich enough for arithmetic contains true statements it cannot prove.
mathematics | Prime number theorem | The number of primes below x is asymptotic to x/ln x.
mathematics | Divergence theorem | ∮ F·dA = ∫ ∇·F dV.
mathematics | Stokes' theorem | ∮ F·dl = ∫ (∇×F)·dA.
physics | Newton's first law | A body remains at rest or in uniform motion unless acted on by a net force.
physics | Newton's third law | For every action there is an equal and opposite reaction.
physics | Conservation of energy | The total energy of an isolated system is constant.
physics | Conservation of momentum | The total momentum of an isolated system is constant.
physics | Conservation of charge | Electric charge is neither created nor destroyed.
physics | Second law of thermodynamics | The entropy of an isolated system never decreases.
physics | Third law of thermodynamics | The entropy of a perfect crystal approaches zero as T → 0 K.
physics | Zeroth law of thermodynamics | Two systems each in thermal equilibrium with a third are in equilibrium with each other.
physics | Principle of least action | Physical trajectories make the action S = ∫ L dt stationary; Euler–Lagrange: d/dt(∂L/∂q̇) = ∂L/∂q.
physics | Maxwell's equations | ∇·E = ρ/ε₀, ∇·B = 0, ∇×E = −∂B/∂t, ∇×B = μ₀J + μ₀ε₀∂E/∂t.
physics | Schrödinger equation | iħ ∂ψ/∂t = Ĥψ; the wavefunction's evolution is unitary and linear.
physics | Born rule | The probability density of a measurement outcome is |ψ|².
physics | Pauli exclusion principle | No two identical fermions occupy the same quantum state.
physics | Einstein field equations | G_μν + Λg_μν = (8πG/c⁴) T_μν: matter-energy curves spacetime.
physics | Principle of relativity | The laws of physics are identical in all inertial frames; c is the same for all observers.
physics | Equivalence principle | Gravitational and inertial mass are identical; free fall is locally indistinguishable from inertial motion.
physics | Standard Model | Matter is quarks and leptons; forces are carried by gauge bosons of SU(3)×SU(2)×U(1); mass arises via the Higgs mechanism.
physics | Four fundamental interactions | Gravity, electromagnetism, weak and strong nuclear forces.
chemistry | Periodic law | Element properties recur periodically with atomic number, reflecting electron shell structure.
chemistry | Conservation of mass in reactions | Atoms are rearranged, not created or destroyed, in chemical reactions.
chemistry | Le Chatelier's principle | A system at equilibrium shifts to counteract an imposed change.
chemistry | Aufbau principle and Hund's rule | Electrons fill lowest-energy orbitals first and occupy degenerate orbitals singly with parallel spins first.
chemistry | Chemical bonding | Ionic, covalent and metallic bonds arise from electrostatics and quantum sharing of electrons; VSEPR predicts molecular geometry.
chemistry | Hess's law | Reaction enthalpy is path-independent: sum the enthalpies of component steps.
chemistry | Avogadro's law | Equal volumes of gases at equal T and P contain equal numbers of molecules.
biology | Cell theory | All living things are made of cells; cells arise only from pre-existing cells.
biology | Evolution by natural selection | Heritable variation plus differential reproductive success produces adaptation and common descent.
biology | Central dogma of molecular biology | Information flows DNA → RNA → protein (with reverse transcription as an exception).
biology | Genetic code | Triplet codons of nucleotides map to 20 amino acids; the code is nearly universal.
biology | Mendelian inheritance | Genes come in alleles that segregate and (when unlinked) assort independently.
biology | Homeostasis | Organisms regulate internal variables via negative feedback.
biology | Energy flow in ecosystems | Energy flows one way from producers through trophic levels with ~10% transfer efficiency; matter cycles.
biology | Germ theory of disease | Many diseases are caused by microorganisms.
biology | Chemiosmosis | ATP synthesis is driven by proton gradients across membranes.
earth_science | Plate tectonics | The lithosphere is divided into plates moving over the asthenosphere, driving earthquakes, volcanism and mountain building.
earth_science | Uniformitarianism | The same physical processes operating today shaped Earth in the past.
earth_science | Law of superposition | In undisturbed strata, younger layers lie above older ones.
earth_science | Greenhouse effect | Atmospheric gases absorb and re-emit infrared radiation, warming the surface.
earth_science | Rock cycle | Igneous, sedimentary and metamorphic rocks transform into one another.
astronomy | Big Bang cosmology | The universe expanded from a hot dense state ~13.8 billion years ago; evidence: CMB, Hubble expansion, light-element abundances.
astronomy | Stellar nucleosynthesis | Stars fuse hydrogen into helium and heavier elements; the heaviest form in supernovae and neutron-star mergers.
astronomy | Kepler's first law | Planets move on ellipses with the Sun at one focus.
astronomy | Kepler's second law | A line from Sun to planet sweeps equal areas in equal times (conservation of angular momentum).
information | Shannon source coding theorem | Data can be compressed to its entropy H = −Σ p log₂ p bits per symbol but no further.
information | Church–Turing thesis | Any effectively computable function is computable by a Turing machine.
method | Scientific method | Observe, hypothesise, predict, test by experiment, revise; claims must be falsifiable and reproducible.
method | Dimensional homogeneity | Every valid physical equation has identical dimensions on both sides; functions like exp, log, sin take dimensionless arguments.
"""
