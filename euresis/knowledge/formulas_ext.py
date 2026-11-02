"""Knowledge expansion, volume 2: more laws across every field.

Same line format as formulas.py:  domain | name | equation | symbol:quantity ...
"""

FORMULAS_EXT = r"""
# ---------------------------------------------------------------- geometry
geometry | Area of a circle | A = pi*r**2 | A:area r:radius
geometry | Circumference of a circle | C = 2*pi*r | C:length r:radius
geometry | Surface area of a sphere | A = 4*pi*r**2 | A:area r:radius
geometry | Volume of a sphere | V = 4*pi*r**3/3 | V:volume r:radius
geometry | Volume of a cylinder | V = pi*r**2*h_ | V:volume r:radius h_:height
geometry | Volume of a cone | V = pi*r**2*h_/3 | V:volume r:radius h_:height
geometry | Arc length | s = r*theta | s:length r:radius theta:angle
geometry | Area of a triangle | A = b*h_/2 | A:area b:length h_:height
geometry | Angular size | theta = D_/d | theta:angle D_:diameter d:distance
# ---------------------------------------------------------------- mechanics
mechanics | Average velocity | v = d/t | v:velocity d:distance t:time
mechanics | Average acceleration | a = dv/t | a:acceleration dv:velocity_change t:time
mechanics | Angular displacement | theta = omega*t | theta:angle omega:angular_velocity t:time
mechanics | Projectile range | R_ = v**2*sin(2*theta)/g | R_:range v:initial_velocity theta:angle g:gravitational_acceleration
mechanics | Projectile maximum height | h_ = v**2*sin(theta)**2/(2*g) | h_:height v:initial_velocity theta:angle g:gravitational_acceleration
mechanics | Tsiolkovsky rocket equation | dv = v_e*log(m0/mf) | dv:velocity_change v_e:exhaust_velocity m0:initial_mass mf:final_mass
mechanics | Rocket thrust | F = mdot*v_e | F:thrust mdot:mass_flow_rate v_e:exhaust_velocity
mechanics | Centripetal force | F = m*v**2/r | F:centripetal_force m:mass v:velocity r:radius
mechanics | Rotational power | P = tau*omega | P:power tau:torque omega:angular_velocity
mechanics | Reduced mass | mu_r = m1*m2/(m1 + m2) | mu_r:reduced_mass m1:mass1 m2:mass2
mechanics | Moment of inertia of a solid sphere | I = 2*m*r**2/5 | I:moment_of_inertia m:mass r:radius
mechanics | Moment of inertia of a thin rod (centre) | I = m*L**2/12 | I:moment_of_inertia m:mass L:length
mechanics | Moment of inertia of a solid disk | I = m*r**2/2 | I:moment_of_inertia m:mass r:radius
mechanics | Physical pendulum period | T = 2*pi*sqrt(I/(m*g*d)) | T:period I:moment_of_inertia m:mass g:gravitational_acceleration d:distance
mechanics | Damped oscillator decay time | tau = 2*m/b | tau:time_constant m:mass b:damping_coefficient
mechanics | Quality factor of an oscillator | Q_ = omega*m/b | Q_:quality_factor omega:angular_frequency m:mass b:damping_coefficient
mechanics | Static friction limit | f = mu*N | f:friction_force mu:static_friction_coefficient N:normal_force
mechanics | Orbital period of a circular orbit | T = 2*pi*r/v | T:period r:radius v:orbital_velocity
# -------------------------------------------------------------- gravitation
gravitation | Vis-viva equation | v**2 = G*M*(2/r - 1/a) | v:orbital_velocity M:mass r:distance a:semi_major_axis
gravitation | Orbital energy | E = -G*M*m/(2*a) | E:energy M:mass1 m:mass2 a:semi_major_axis
gravitation | Tidal acceleration | a_t = 2*G*M*d/r**3 | a_t:tidal_acceleration M:mass d:length r:distance
gravitation | Hill sphere radius | r_H = a*(m/(3*M))**(1/3) | r_H:hill_radius a:semi_major_axis m:mass1 M:mass2
gravitation | Roche limit (rigid body) | d = R_*(2*rho_M/rho_m)**(1/3) | d:roche_limit R_:radius rho_M:primary_density rho_m:satellite_density
gravitation | Gravitational binding energy of a uniform sphere | U = 3*G*M**2/(5*R_) | U:binding_energy M:mass R_:radius
gravitation | Free-fall collapse time | t = sqrt(3*pi/(32*G*rho)) | t:free_fall_time rho:density
gravitation | Gravitational redshift (weak field) | z = G*M/(r*c**2) | z:redshift M:mass r:radius
gravitation | Gravitational time dilation | t0 = t*sqrt(1 - 2*G*M/(r*c**2)) | t0:proper_time t:time M:mass r:radius
gravitation | Light deflection by a mass | theta = 4*G*M/(b_*c**2) | theta:deflection_angle M:mass b_:impact_parameter
gravitation | Photon sphere radius | r = 3*G*M/c**2 | r:photon_sphere_radius M:mass
gravitation | Innermost stable circular orbit | r = 6*G*M/c**2 | r:isco_radius M:mass
# --------------------------------------------------------------- relativity
relativity | Relativistic kinetic energy | K = (gamma_ - 1)*m*c**2 | K:kinetic_energy gamma_:lorentz_factor m:mass
relativity | Total relativistic energy | E = gamma_*m*c**2 | E:energy gamma_:lorentz_factor m:mass
relativity | Relativistic velocity addition | u = (v + w)/(1 + v*w/c**2) | u:final_velocity v:velocity w:initial_velocity
relativity | Relativistic Doppler effect | f_o = f_s*sqrt((c - v)/(c + v)) | f_o:observed_frequency f_s:frequency v:velocity
# ------------------------------------------------------------------ quantum
quantum | Wavenumber | k = 2*pi/lam | k:wavenumber lam:wavelength
quantum | Photon energy from wavelength | E = h*c/lam | E:photon_energy lam:wavelength
quantum | Rydberg formula | 1/lam = R_inf*(1/n1**2 - 1/n2**2) | lam:wavelength n1:quantum_number_lower n2:quantum_number
quantum | Tunnelling decay constant | kappa = sqrt(2*m*(V0 - E))/hbar | kappa:wavenumber m:mass V0:potential_energy E:energy
quantum | Tunnelling probability | T_ = exp(-2*kappa*L) | T_:transmission_probability kappa:wavenumber L:length
quantum | Thermal de Broglie wavelength | lam = h/sqrt(2*pi*m*k_B*T) | lam:thermal_wavelength m:mass T:temperature
quantum | Zero-point energy | E = hbar*omega/2 | E:zero_point_energy omega:angular_frequency
quantum | Hydrogen-like energy levels | E = -Z**2*E_R/n**2 | E:energy_level Z:atomic_number n:quantum_number
quantum | Bohr magneton | mu_B = e*hbar/(2*m_e) |
quantum | Larmor precession frequency | omega = g_*mu_B*B/hbar | omega:angular_frequency g_:g_factor B:magnetic_field
quantum | Magnetic dipole energy | U = mu*B | U:potential_energy mu:magnetic_moment B:magnetic_field
quantum | Magnetic moment of a current loop | mu = I*A | mu:magnetic_moment I:current A:area
quantum | Pair production threshold | E = 2*m_e*c**2 | E:threshold_energy
# ----------------------------------------------------- statistical mechanics
statistical_mechanics | Equipartition theorem (per quadratic degree of freedom) | E = k_B*T/2 | E:energy T:temperature
statistical_mechanics | Most probable molecular speed | v = sqrt(2*k_B*T/m) | v:velocity T:temperature m:mass
statistical_mechanics | Mean molecular speed | v = sqrt(8*k_B*T/(pi*m)) | v:velocity T:temperature m:mass
statistical_mechanics | Mean free path of a gas | lam = k_B*T/(sqrt(2)*pi*d**2*P) | lam:mean_free_path T:temperature d:molecular_diameter P:pressure
statistical_mechanics | Fermi energy of a free electron gas | E_F = hbar**2*(3*pi**2*n)**(2/3)/(2*m_e) | E_F:fermi_energy n:number_density
statistical_mechanics | Kinetic theory pressure | P = N*m*v**2/(3*V) | P:pressure N:number m:mass v:velocity V:volume
statistical_mechanics | Planck's law of black-body radiation | B = 2*h*c**2/(lam**5*(exp(h*c/(lam*k_B*T)) - 1)) | B:spectral_radiance lam:wavelength T:temperature
statistical_mechanics | Rayleigh-Jeans law | B = 2*c*k_B*T/lam**4 | B:spectral_radiance lam:wavelength T:temperature
# ----------------------------------------------------------- thermodynamics
thermodynamics | Helmholtz free energy | A_ = U - T*S | A_:helmholtz_energy U:internal_energy T:temperature S:entropy
thermodynamics | Enthalpy | H = U + P*V | H:total_enthalpy U:internal_energy P:pressure V:volume
thermodynamics | Van der Waals equation of state | (P + a_*n**2/V**2)*(V - n*b_) = n*R*T | P:pressure a_:vdw_a n:amount V:volume b_:vdw_b T:temperature
thermodynamics | Clausius-Clapeyron equation | log(P2/P1) = -L*(1/T2 - 1/T1)/R | P2:pressure P1:pressure L:molar_latent_heat T2:temperature T1:temperature
thermodynamics | Carnot refrigerator coefficient of performance | K_ = Tc/(Th - Tc) | K_:coefficient_of_performance Tc:temperature_cold Th:temperature_hot
thermodynamics | Otto cycle efficiency | eta = 1 - r_c**(1 - gamma_) | eta:efficiency r_c:compression_ratio gamma_:heat_capacity_ratio
thermodynamics | Linear thermal expansion | dL = alpha_t*L*dT | dL:displacement alpha_t:thermal_expansion_coefficient L:length dT:temperature_change
thermodynamics | Newton's law of cooling | P = h_c*A*dT | P:heat_flow h_c:heat_transfer_coefficient A:area dT:temperature_change
thermodynamics | Thermal diffusivity | alpha_d = k/(rho*c_) | alpha_d:thermal_diffusivity k:thermal_conductivity rho:density c_:specific_heat
thermodynamics | Thermal diffusion time | t = L**2/alpha_d | t:time L:length alpha_d:thermal_diffusivity
thermodynamics | Ideal entropy of mixing (binary) | dS = -n*R*(x*log(x) + (1 - x)*log(1 - x)) | dS:entropy_change n:amount x:mole_fraction
# --------------------------------------------------------- electromagnetism
electromagnetism | Field at the centre of a current loop | B = mu_0*I/(2*r) | B:magnetic_field I:current r:radius
electromagnetism | Inductance of a solenoid | L = mu_0*N**2*A/l | L:inductance N:turns A:area l:length
electromagnetism | Magnetic pressure | P = B**2/(2*mu_0) | P:pressure B:magnetic_field
electromagnetism | Poynting vector magnitude | S = E*B/mu_0 | S:intensity E:electric_field B:magnetic_field
electromagnetism | Radiation pressure (absorbed light) | P = I/c | P:pressure I:intensity
electromagnetism | Larmor radiated power | P = q**2*a**2/(6*pi*epsilon_0*c**3) | P:power q:charge a:acceleration
electromagnetism | Plasma frequency | omega = sqrt(n*e**2/(epsilon_0*m_e)) | omega:plasma_frequency n:number_density
electromagnetism | Debye length | lam_D = sqrt(epsilon_0*k_B*T/(n*e**2)) | lam_D:debye_length T:temperature n:number_density
electromagnetism | Skin depth | delta = sqrt(2*rho/(omega*mu_0)) | delta:skin_depth rho:resistivity omega:angular_frequency
electromagnetism | Hall voltage | V = I*B/(n*e*t_) | V:voltage I:current B:magnetic_field n:number_density t_:thickness
electromagnetism | Drift velocity | I = n*e*A*v | I:current n:number_density A:area v:drift_velocity
electromagnetism | Electric dipole moment | p = q*d | p:dipole_moment q:charge d:distance
electromagnetism | Torque on an electric dipole | tau = p*E*sin(theta) | tau:torque p:dipole_moment E:electric_field theta:angle
electromagnetism | Field of a dipole (on axis, far) | E = 2*k_e*p/r**3 | E:electric_field p:dipole_moment r:distance
electromagnetism | Field of an infinite charged sheet | E = sigma_c/(2*epsilon_0) | E:electric_field sigma_c:surface_charge_density
electromagnetism | Cyclotron frequency | omega = q*B/m | omega:angular_frequency q:charge B:magnetic_field m:mass
electromagnetism | Motional EMF | emf = B*L*v | emf:emf B:magnetic_field L:length v:velocity
electromagnetism | Self-induced EMF | emf = L*I/t | emf:emf L:inductance I:current t:time
electromagnetism | Impedance of free space | Z0 = sqrt(mu_0/epsilon_0) | Z0:impedance
circuits | Resistors in series | R_ = R1 + R2 | R_:resistance R1:resistance R2:resistance
circuits | Resistors in parallel | R_ = R1*R2/(R1 + R2) | R_:resistance R1:resistance R2:resistance
circuits | Capacitors in series | C = C1*C2/(C1 + C2) | C:capacitance C1:capacitance C2:capacitance
circuits | Inductive reactance | X = omega*L | X:reactance omega:angular_frequency L:inductance
circuits | Capacitive reactance | X = 1/(omega*C) | X:reactance omega:angular_frequency C:capacitance
circuits | Ideal transformer | V2/V1 = N2/N1 | V2:voltage V1:voltage N2:turns N1:turns
circuits | Johnson-Nyquist thermal noise | V**2 = 4*k_B*T*R_*B_ | V:noise_voltage T:temperature R_:resistance B_:bandwidth
# ---------------------------------------------------------- waves & optics
optics | Rayleigh resolution criterion | theta = 1.22*lam/D_ | theta:angle lam:wavelength D_:diameter
optics | Bragg's law | 2*d*sin(theta) = n*lam | d:lattice_spacing theta:angle n:order lam:wavelength
optics | Malus's law | I = I0*cos(theta)**2 | I:intensity I0:intensity theta:angle
optics | Brewster's angle | tan(theta) = n2/n1 | theta:angle n2:refractive_index2 n1:refractive_index1
optics | Critical angle for total internal reflection | sin(theta) = n2/n1 | theta:angle n2:refractive_index2 n1:refractive_index1
optics | Optical power of a lens | P_ = 1/f | P_:optical_power f:focal_length
optics | Lensmaker's equation | 1/f = (n - 1)*(1/R1 - 1/R2) | f:focal_length n:refractive_index R1:radius_of_curvature R2:radius_of_curvature
waves | Doppler effect (moving source) | f_o = f_s*v/(v - v_s) | f_o:observed_frequency f_s:frequency v:speed_of_sound v_s:source_velocity
waves | Standing waves on a string | f = n*v/(2*L) | f:frequency n:order v:wave_speed L:length
waves | Sound intensity level | beta = 10*log(I/I0)/log(10) | beta:sound_level I:intensity I0:intensity
waves | Speed of sound in a solid rod | v = sqrt(Y/rho) | v:speed_of_sound Y:youngs_modulus rho:density
waves | Speed of sound in a fluid | v = sqrt(K/rho) | v:speed_of_sound K:bulk_modulus rho:density
waves | Deep-water wave speed | v = sqrt(g*lam/(2*pi)) | v:wave_speed g:gravitational_acceleration lam:wavelength
waves | Shallow-water wave speed | v = sqrt(g*h_) | v:wave_speed g:gravitational_acceleration h_:depth
waves | Capillary wave speed | v = sqrt(2*pi*gamma_s/(rho*lam)) | v:wave_speed gamma_s:surface_tension rho:density lam:wavelength
# ------------------------------------------------------------------- fluids
fluids | Torricelli's law | v = sqrt(2*g*h_) | v:velocity g:gravitational_acceleration h_:height
fluids | Stokes terminal velocity | v = 2*(rho_p - rho)*g*r**2/(9*eta_) | v:terminal_velocity rho_p:particle_density rho:density g:gravitational_acceleration r:radius eta_:viscosity
fluids | Terminal velocity (quadratic drag) | v = sqrt(2*m*g/(rho*C_d*A)) | v:terminal_velocity m:mass g:gravitational_acceleration rho:density C_d:drag_coefficient A:area
fluids | Capillary rise (Jurin's law) | h_ = 2*gamma_s*cos(theta)/(rho*g*r) | h_:height gamma_s:surface_tension theta:angle rho:density g:gravitational_acceleration r:radius
fluids | Mach number | Ma = v/c_s | Ma:mach_number v:velocity c_s:speed_of_sound
fluids | Froude number | Fr = v/sqrt(g*L) | Fr:froude_number v:velocity g:gravitational_acceleration L:length
fluids | Weber number | We = rho*v**2*L/gamma_s | We:weber_number rho:density v:velocity L:length gamma_s:surface_tension
fluids | Strouhal number | St = f*L/v | St:strouhal_number f:frequency L:length v:velocity
fluids | Kinematic viscosity | nu = eta_/rho | nu:kinematic_viscosity eta_:viscosity rho:density
fluids | Mass flow rate | mdot = rho*A*v | mdot:mass_flow_rate rho:density A:area v:velocity
fluids | Darcy's law | Q = k_p*A*P/(eta_*L) | Q:flow_rate k_p:permeability A:area P:pressure eta_:viscosity L:length
# ---------------------------------------------------------------- materials
materials | Shear modulus | G_ = tau_s/gamma_sh | G_:shear_modulus tau_s:shear_stress gamma_sh:shear_strain
materials | Bulk modulus definition | K = P*V/dV | K:bulk_modulus P:pressure V:volume dV:volume_change
materials | Elastic energy density | u = sigma_s**2/(2*Y) | u:energy_density sigma_s:stress Y:youngs_modulus
materials | Euler buckling load | F = pi**2*Y*I_a/(K_*L)**2 | F:force Y:youngs_modulus I_a:area_moment K_:effective_length_factor L:length
materials | Thermal stress | sigma_s = Y*alpha_t*dT | sigma_s:stress Y:youngs_modulus alpha_t:thermal_expansion_coefficient dT:temperature_change
materials | Griffith fracture stress | sigma_s = sqrt(2*Y*gamma_e/(pi*a)) | sigma_s:stress Y:youngs_modulus gamma_e:surface_energy a:crack_length
# ------------------------------------------------------ astrophysics/cosmo
astrophysics | Hawking temperature of a black hole | T = hbar*c**3/(8*pi*G*M*k_B) | T:temperature M:mass
astrophysics | Bekenstein-Hawking entropy | S = k_B*c**3*A/(4*G*hbar) | S:entropy A:area
astrophysics | Eddington luminosity | L = 4*pi*G*M*m_p*c/sigma_T | L:luminosity M:mass
astrophysics | Jeans mass | M = (5*k_B*T/(G*m))**(3/2)*(3/(4*pi*rho))**(1/2) | M:jeans_mass T:temperature m:particle_mass rho:density
astrophysics | Jeans length | lam = sqrt(15*k_B*T/(4*pi*G*m*rho)) | lam:jeans_length T:temperature m:particle_mass rho:density
astrophysics | Virial theorem | K = -U/2 | K:kinetic_energy U:potential_energy
astrophysics | Critical density of the universe | rho = 3*H**2/(8*pi*G) | rho:critical_density H:hubble_constant
astrophysics | Friedmann equation | H**2 = 8*pi*G*rho/3 - k*c**2/a**2 | H:hubble_constant rho:density k:curvature_index a:curvature_radius
astrophysics | Cosmological redshift and scale factor | 1 + z = 1/a | z:redshift a:scale_factor
astrophysics | Mass-luminosity relation (main sequence) | L/L_sun = (M/M_sun)**(7/2) | L:luminosity M:mass
astrophysics | Main-sequence lifetime | t = 10000000000*yr*(M/M_sun)**(-5/2) | t:stellar_lifetime M:mass
astrophysics | Chandrasekhar limit | M = 2.018*sqrt(3*pi)/2*(hbar*c/G)**(3/2)/(2*m_p)**2 | M:chandrasekhar_mass
astrophysics | Synodic period | 1/S = 1/T1 - 1/T2 | S:synodic_period T1:period T2:period
astrophysics | Solar constant | S = L_sun/(4*pi*AU**2) | S:flux
# ---------------------------------------------------------- nuclear/particle
nuclear | Reaction Q-value | Q = (m_i - m_f)*c**2 | Q:reaction_energy m_i:initial_mass m_f:final_mass
nuclear | Semi-empirical mass formula | E = a_v*A_ - a_s*A_**(2/3) - a_c*Z**2/A_**(1/3) - a_a*(A_ - 2*Z)**2/A_ | E:binding_energy A_:mass_number Z:atomic_number
nuclear | Coulomb barrier | E = k_e*Z1*Z2*e**2/r | E:barrier_energy Z1:atomic_number Z2:atomic_number2 r:distance
nuclear | Gamow energy | E = 2*mu_r*c**2*(pi*alpha*Z1*Z2)**2 | E:gamow_energy mu_r:reduced_mass Z1:atomic_number Z2:atomic_number2
nuclear | Beam attenuation | I = I0*exp(-n*sigma_x*x) | I:intensity I0:intensity n:number_density sigma_x:cross_section x:length
nuclear | Mean free path from cross-section | lam = 1/(n*sigma_x) | lam:mean_free_path n:number_density sigma_x:cross_section
# ---------------------------------------------------------------- chemistry
chemistry | Graham's law of effusion | r1/r2 = sqrt(M2/M1) | r1:effusion_rate r2:effusion_rate M1:molar_mass M2:molar_mass
chemistry | Combined gas law | P1*V1/T1 = P2*V2/T2 | P1:pressure V1:volume T1:temperature P2:pressure V2:volume T2:temperature
chemistry | Ideal gas density | rho = P*M/(R*T) | rho:density P:pressure M:molar_mass T:temperature
chemistry | Eyring equation | k = kappa_*k_B*T*exp(-G_/(R*T))/h | k:rate_constant kappa_:transmission_coefficient T:temperature G_:activation_gibbs_energy
chemistry | First-order rate law | r = k*c | r:reaction_velocity k:rate_constant c:concentration
chemistry | Second-order integrated rate law | 1/c = 1/c0 + k2*t | c:concentration c0:concentration k2:second_order_rate_constant t:time
chemistry | Second-order half-life | t_h = 1/(k2*c0) | t_h:half_life k2:second_order_rate_constant c0:concentration
chemistry | Zero-order integrated rate law | c = c0 - k0*t | c:concentration c0:concentration k0:reaction_velocity t:time
chemistry | Van 't Hoff equation | log(K2/K1) = -dH*(1/T2 - 1/T1)/R | K2:equilibrium_constant K1:equilibrium_constant dH:enthalpy T2:temperature T1:temperature
chemistry | Boiling point elevation | dT = i*K_b*b | dT:boiling_point_elevation i:vant_hoff_factor K_b:ebullioscopic_constant b:molality
chemistry | Mass deposited in electrolysis | m = Q*M/(z*F_c) | m:mass Q:charge M:molar_mass z:electrons_transferred
chemistry | pKa definition | pKa = -log(Ka)/log(10) | pKa:pka Ka:acid_dissociation_constant
chemistry | Dilution | c1*V1 = c2*V2 | c1:concentration V1:volume c2:concentration V2:volume
chemistry | Gibbs phase rule | F_ = C_ - P_ + 2 | F_:degrees_of_freedom C_:components P_:phases
# ------------------------------------------------------------------ biology
biology | Fick's first law of diffusion | J = D_*c/L | J:molar_flux D_:diffusion_coefficient c:concentration L:length
biology | Diffusion time | t = L**2/(2*D_) | t:time L:length D_:diffusion_coefficient
biology | Lotka-Volterra prey equation | dxdt = a_*x - b_*x*y | dxdt:population_rate a_:growth_rate x:population b_:predation_rate y:predator_population
biology | Lotka-Volterra predator equation | dydt = d_*x*y - g_*y | dydt:predator_rate d_:predator_efficiency x:population y:predator_population g_:predator_death_rate
biology | Allometric heart rate | f = a_*M**(-1/4) | f:heart_rate a_:heart_rate_coefficient M:mass
biology | Allometric lifespan | t = a_*M**(1/4) | t:lifespan a_:lifespan_coefficient M:mass
biology | Monod growth equation | mu_g = mu_max*S/(K_s + S) | mu_g:growth_rate mu_max:max_growth_rate S:substrate_concentration K_s:michaelis_constant
biology | Neuronal length constant (cable theory) | lam = sqrt(r_m/r_i) | lam:length_constant r_m:membrane_resistance_length r_i:axial_resistance_per_length
biology | Membrane time constant | tau = R_m*C_m | tau:time_constant R_m:specific_membrane_resistance C_m:specific_membrane_capacitance
biology | SIR infection dynamics | di = beta*s*i - gamma_r*i | di:infection_rate beta:transmission_rate s:susceptible_fraction i:infected_fraction gamma_r:recovery_rate
biology | Hardy-Weinberg homozygote frequency | P_ = p**2 | P_:genotype_frequency p:allele_p
biology | Hardy-Weinberg heterozygote frequency | P_ = 2*p*q | P_:heterozygote_frequency p:allele_p q:allele_q
biology | Mutation-selection balance | q = sqrt(mu_m/s_) | q:allele_q mu_m:mutation_rate s_:selection_coefficient
biology | Fixation probability of a beneficial mutation | P_ = 2*s_ | P_:fixation_probability s_:selection_coefficient
biology | Neutral fixation probability | P_ = 1/(2*N_e) | P_:fixation_probability N_e:effective_population_size
biology | Molecular clock | d = 2*mu_r*t | d:genetic_distance mu_r:substitution_rate t:time
biology | Law of Laplace (blood vessel) | T_w = P*r | T_w:wall_tension P:pressure r:radius
biology | Cardiac output | Q = HR*SV | Q:flow_rate HR:heart_rate SV:stroke_volume
biology | Haemodynamic Ohm's law | P = Q*R_v | P:pressure Q:flow_rate R_v:vascular_resistance
biology | Competitive inhibition | v = Vmax*S/(Km*(1 + I_/Ki) + S) | v:reaction_velocity Vmax:max_velocity S:substrate_concentration Km:michaelis_constant I_:inhibitor_concentration Ki:inhibition_constant
biology | Species-area relationship | S_n = c_*(A/A0)**z_ | S_n:species_count c_:species_coefficient A:area A0:area z_:species_area_exponent
# ------------------------------------------------------------ earth science
earth_science | Coriolis parameter | f_c = 2*Omega*sin(phi) | f_c:coriolis_parameter Omega:angular_velocity phi:angle
earth_science | Geostrophic wind | v = P/(rho*f_c*L) | v:velocity P:pressure rho:density f_c:coriolis_parameter L:length
earth_science | Rossby number | Ro = v/(f_c*L) | Ro:rossby_number v:velocity f_c:coriolis_parameter L:length
earth_science | Airy isostasy | r_ = h_*rho_c/(rho_m - rho_c) | r_:depth h_:height rho_c:crust_density rho_m:mantle_density
earth_science | Geothermal heat flux | q = k*dT/z_ | q:heat_flux k:thermal_conductivity dT:temperature_change z_:depth
earth_science | Planetary equilibrium temperature | T = (S*(1 - A_)/(4*eps*sigma))**(1/4) | T:temperature S:flux A_:albedo eps:emissivity
earth_science | Radiometric dating | t = log(1 + r_)/lam_ | t:time r_:daughter_parent_ratio lam_:decay_constant
earth_science | Seismic P-wave speed | v = sqrt((K + 4*G_/3)/rho) | v:wave_speed K:bulk_modulus G_:shear_modulus rho:density
earth_science | Seismic S-wave speed | v = sqrt(G_/rho) | v:wave_speed G_:shear_modulus rho:density
earth_science | Earthquake energy-magnitude relation | log(E_)/log(10) = 3*Mw/2 + 4.8 | E_:seismic_energy_value Mw:moment_magnitude
earth_science | Climate sensitivity | dT = lam_c*dF | dT:temperature_change lam_c:climate_sensitivity_parameter dF:radiative_forcing
earth_science | CO2 radiative forcing | dF = a_F*log(C/C0) | dF:radiative_forcing a_F:forcing_coefficient C:co2_concentration C0:co2_concentration
# ------------------------------------------------------- information/computation
information | Shannon-Hartley channel capacity | C = B_*log(1 + SNR)/log(2) | C:channel_capacity B_:bandwidth SNR:signal_to_noise
information | Nyquist sampling rate | f_s = 2*f | f_s:sampling_frequency f:frequency
information | Bremermann's limit | rate = m*c**2/h | rate:computation_rate m:mass
information | Margolus-Levitin bound | rate = 2*E/(pi*hbar) | rate:computation_rate E:energy
information | Bekenstein bound | I = 2*pi*R_*E/(hbar*c*log(2)) | I:information R_:radius E:energy
information | Binary entropy function | H_ = -(p*log(p) + (1 - p)*log(1 - p))/log(2) | H_:shannon_entropy p:probability
"""

QUANTITIES_EXT = """
diameter | diameter | L
range | horizontal range | L
velocity_change | change in velocity | L T-1
exhaust_velocity | exhaust velocity | L T-1
initial_mass | initial mass | M
final_mass | final mass | M
thrust | thrust | M L T-2
centripetal_force | centripetal force | M L T-2
mass_flow_rate | mass flow rate | M T-1
reduced_mass | reduced mass | M
damping_coefficient | damping coefficient | M T-1
quality_factor | quality factor | 1
static_friction_coefficient | coefficient of static friction | 1
tidal_acceleration | tidal acceleration | L T-2
hill_radius | Hill sphere radius | L
roche_limit | Roche limit | L
primary_density | density of primary body | M L-3
satellite_density | density of satellite | M L-3
free_fall_time | free-fall time | T
deflection_angle | light deflection angle | 1
impact_parameter | impact parameter | L
photon_sphere_radius | photon sphere radius | L
isco_radius | innermost stable circular orbit radius | L
observed_frequency | observed frequency | T-1
wavenumber | wavenumber | L-1
quantum_number_lower | lower principal quantum number | 1
transmission_probability | transmission probability | 1
thermal_wavelength | thermal de Broglie wavelength | L
zero_point_energy | zero-point energy | M L2 T-2
g_factor | g-factor | 1
magnetic_moment | magnetic moment | I L2
threshold_energy | threshold energy | M L2 T-2
mean_free_path | mean free path | L
molecular_diameter | molecular diameter | L
fermi_energy | Fermi energy | M L2 T-2
spectral_radiance | spectral radiance | M L-1 T-3
helmholtz_energy | Helmholtz free energy | M L2 T-2
total_enthalpy | enthalpy | M L2 T-2
vdw_a | van der Waals a | M L5 T-2 N-2
vdw_b | van der Waals b | L3 N-1
molar_latent_heat | molar latent heat | M L2 T-2 N-1
coefficient_of_performance | coefficient of performance | 1
compression_ratio | compression ratio | 1
thermal_expansion_coefficient | thermal expansion coefficient | K-1
heat_transfer_coefficient | heat transfer coefficient | M T-3 K-1
thermal_diffusivity | thermal diffusivity | L2 T-1
plasma_frequency | plasma frequency | T-1
debye_length | Debye length | L
skin_depth | skin depth | L
thickness | thickness | L
drift_velocity | drift velocity | L T-1
dipole_moment | electric dipole moment | I T L
surface_charge_density | surface charge density | I T L-2
impedance | impedance | M L2 T-3 I-2
reactance | reactance | M L2 T-3 I-2
noise_voltage | thermal noise voltage | M L2 T-3 I-1
bandwidth | bandwidth | T-1
lattice_spacing | lattice spacing | L
optical_power | optical power | L-1
radius_of_curvature | radius of curvature | L
source_velocity | source velocity | L T-1
sound_level | sound intensity level (dB) | 1
terminal_velocity | terminal velocity | L T-1
particle_density | particle density | M L-3
mach_number | Mach number | 1
froude_number | Froude number | 1
weber_number | Weber number | 1
strouhal_number | Strouhal number | 1
kinematic_viscosity | kinematic viscosity | L2 T-1
permeability | permeability | L2
shear_modulus | shear modulus | M L-1 T-2
shear_stress | shear stress | M L-1 T-2
shear_strain | shear strain | 1
volume_change | volume change | L3
area_moment | second moment of area | L4
effective_length_factor | effective length factor | 1
surface_energy | surface energy | M T-2
crack_length | crack half-length | L
jeans_mass | Jeans mass | M
jeans_length | Jeans length | L
particle_mass | particle mass | M
critical_density | critical density | M L-3
curvature_index | curvature index | 1
curvature_radius | curvature radius | L
scale_factor | scale factor | 1
stellar_lifetime | main-sequence lifetime | T
chandrasekhar_mass | Chandrasekhar mass | M
synodic_period | synodic period | T
reaction_energy | reaction Q-value | M L2 T-2
barrier_energy | Coulomb barrier energy | M L2 T-2
gamow_energy | Gamow energy | M L2 T-2
atomic_number2 | atomic number of second nucleus | 1
cross_section | cross-section | L2
effusion_rate | effusion rate | N T-1
transmission_coefficient | transmission coefficient | 1
activation_gibbs_energy | Gibbs energy of activation | M L2 T-2 N-1
second_order_rate_constant | second-order rate constant | N-1 L3 T-1
boiling_point_elevation | boiling point elevation | K
ebullioscopic_constant | ebullioscopic constant | K M N-1
acid_dissociation_constant | acid dissociation constant (mol/L) | 1
degrees_of_freedom | thermodynamic degrees of freedom | 1
components | number of components | 1
phases | number of phases | 1
molar_flux | molar flux | N L-2 T-1
predation_rate | predation rate | T-1
predator_population | predator population | 1
predator_rate | predator growth rate | T-1
predator_efficiency | predator efficiency | T-1
predator_death_rate | predator death rate | T-1
heart_rate | heart rate | T-1
heart_rate_coefficient | allometric heart-rate coefficient | T-1 M0.25
lifespan | lifespan | T
lifespan_coefficient | allometric lifespan coefficient | T M-0.25
max_growth_rate | maximum specific growth rate | T-1
length_constant | neuronal length constant | L
membrane_resistance_length | membrane resistance × length | M L3 T-3 I-2
axial_resistance_per_length | axial resistance per length | M L T-3 I-2
specific_membrane_resistance | specific membrane resistance | M L4 T-3 I-2
specific_membrane_capacitance | specific membrane capacitance | M-1 L-4 T4 I2
infection_rate | rate of change of infected fraction | T-1
susceptible_fraction | susceptible fraction | 1
infected_fraction | infected fraction | 1
genotype_frequency | homozygote genotype frequency | 1
heterozygote_frequency | heterozygote frequency | 1
mutation_rate | mutation rate per generation | 1
selection_coefficient | selection coefficient | 1
fixation_probability | fixation probability | 1
effective_population_size | effective population size | 1
genetic_distance | genetic distance | 1
substitution_rate | substitution rate | T-1
wall_tension | wall tension | M T-2
stroke_volume | stroke volume | L3
vascular_resistance | vascular resistance | M L-4 T-1
inhibitor_concentration | inhibitor concentration | N L-3
inhibition_constant | inhibition constant | N L-3
species_count | number of species | 1
species_coefficient | species-area coefficient | 1
species_area_exponent | species-area exponent | 1
coriolis_parameter | Coriolis parameter | T-1
rossby_number | Rossby number | 1
crust_density | crustal density | M L-3
mantle_density | mantle density | M L-3
heat_flux | heat flux | M T-3
albedo | albedo | 1
daughter_parent_ratio | daughter/parent isotope ratio | 1
seismic_energy_value | seismic energy (numeric, J) | 1
climate_sensitivity_parameter | climate sensitivity parameter | K M-1 T3
radiative_forcing | radiative forcing | M T-3
forcing_coefficient | forcing coefficient | M T-3
co2_concentration | CO2 concentration (ppm) | 1
channel_capacity | channel capacity (bits/s) | T-1
signal_to_noise | signal-to-noise ratio | 1
sampling_frequency | sampling frequency | T-1
computation_rate | computation rate (operations/s) | T-1
"""

CONSTANTS_EXT = {
    "sigma_T": ("Thomson cross-section", 6.652_458_7321e-29, "m^2", "L2", False),
    "yr": ("Julian year", 3.155_76e7, "s", "T", True),
    "T_CMB": ("CMB temperature today", 2.7255, "K", "K", False),
    "mu_B": ("Bohr magneton", 9.274_010_0783e-24, "J T^-1", "I L2", False),
    "a_v": ("SEMF volume term", 15.75 * 1.602_176_634e-13, "J", "M L2 T-2", False),
    "a_s": ("SEMF surface term", 17.8 * 1.602_176_634e-13, "J", "M L2 T-2", False),
    "a_c": ("SEMF Coulomb term", 0.711 * 1.602_176_634e-13, "J", "M L2 T-2", False),
    "a_a": ("SEMF asymmetry term", 23.7 * 1.602_176_634e-13, "J", "M L2 T-2", False),
    "R_sun": ("nominal solar radius", 6.957e8, "m", "L", True),
    "pc": ("parsec", 3.085_677_581e16, "m", "L", False),
    "ly": ("light-year", 9.460_730_472_5808e15, "m", "L", True),
    "eV": ("electronvolt", 1.602_176_634e-19, "J", "M L2 T-2", True),
    "Omega_E": ("Earth's rotation rate", 7.292_115_9e-5, "s^-1", "T-1", False),
    "m_mu": ("muon mass", 1.883_531_627e-28, "kg", "M", False),
    "Lambda": ("cosmological constant", 1.1056e-52, "m^-2", "L-2", False),
    "g_e": ("electron g-factor (magnitude)", 2.002_319_304_362_56, "1", "1", False),
}

PRINCIPLES_EXT = """
physics | Huygens' principle | Every point on a wavefront is a source of secondary wavelets; their envelope is the new wavefront.
physics | Fermat's principle | Light travels between two points along the path of stationary optical length.
physics | Pascal's principle | Pressure applied to an enclosed fluid is transmitted undiminished throughout it.
physics | Lenz's law | An induced current flows so as to oppose the change in flux that produced it.
physics | Superposition principle | For linear systems the net response to several stimuli is the sum of the individual responses.
physics | Correspondence principle | Quantum mechanics reproduces classical physics in the limit of large quantum numbers.
physics | Complementarity | Wave and particle descriptions are complementary; which appears depends on the measurement.
physics | Spin-statistics theorem | Integer-spin particles are bosons; half-integer-spin particles are fermions.
physics | CPT symmetry | Every Lorentz-invariant local quantum field theory is invariant under combined charge conjugation, parity and time reversal.
physics | Gauge invariance | The fundamental interactions arise from requiring local symmetry of the quantum fields.
physics | Bell's theorem | No local hidden-variable theory reproduces all predictions of quantum mechanics; experiments confirm the violation of Bell inequalities.
physics | No-cloning theorem | An unknown quantum state cannot be copied perfectly.
physics | Cosmological principle | On large scales the universe is homogeneous and isotropic.
physics | Holographic principle (conjecture) | The information content of a region of space may be bounded by its boundary area in Planck units.
physics | Gravitational waves | Accelerating masses emit ripples in spacetime travelling at c; first detected directly by LIGO in 2015.
physics | Quantum entanglement | Composite quantum systems can have joint states not expressible as products of individual states.
physics | Spontaneous symmetry breaking | A system's ground state can lack the symmetry of its laws, producing phases, massless modes, or masses via the Higgs mechanism.
physics | Renormalization group | Physical theories change systematically with the scale of observation; universality explains why diverse systems share critical exponents.
chemistry | Octet rule | Main-group atoms tend to gain, lose or share electrons to attain eight valence electrons.
chemistry | VSEPR theory | Electron pairs around a central atom arrange to minimise repulsion, fixing molecular geometry.
chemistry | Hammond's postulate | A transition state resembles the stable species nearest to it in energy.
chemistry | Hückel's rule | Planar cyclic conjugated systems with 4n+2 π electrons are aromatic.
chemistry | Markovnikov's rule | In HX addition to an alkene, H attaches to the carbon with more hydrogens.
chemistry | Brønsted-Lowry acids and bases | Acids donate protons; bases accept them.
chemistry | Lewis acids and bases | Acids accept electron pairs; bases donate them.
chemistry | Collision theory | Reactions occur when molecules collide with sufficient energy and correct orientation.
chemistry | Transition state theory | Reaction rates are set by a quasi-equilibrium with an activated complex at the saddle point of the energy surface.
chemistry | Electronegativity | Atoms differ in their pull on bonding electrons; differences determine bond polarity.
chemistry | Born-Haber cycle | Lattice energies follow from Hess's law applied to ionisation, electron affinity, sublimation and dissociation steps.
biology | Hardy-Weinberg principle | Allele and genotype frequencies stay constant without selection, mutation, migration, drift or non-random mating.
biology | Hamilton's rule | Altruism is favoured by selection when relatedness × benefit > cost (rB > C).
biology | Neutral theory of molecular evolution | Most molecular variation is selectively neutral and fixed by genetic drift.
biology | Endosymbiotic theory | Mitochondria and chloroplasts descend from free-living bacteria engulfed by ancestral cells.
biology | Competitive exclusion principle | Two species competing for the same limiting resource cannot coexist indefinitely.
biology | Island biogeography | Species richness on islands balances immigration (falling with distance) and extinction (falling with area).
biology | Red Queen hypothesis | Species must continually adapt merely to keep pace with co-evolving competitors and parasites.
biology | DNA double helix | DNA is two antiparallel strands paired A–T and G–C, enabling templated replication.
biology | Action potential | Neurons fire all-or-none spikes via voltage-gated Na⁺ and K⁺ channels (Hodgkin–Huxley).
biology | Hebbian learning | Synapses strengthen when pre- and post-synaptic neurons fire together.
biology | Clonal selection | Antigens select and expand lymphocytes bearing matching receptors, creating adaptive immunity.
biology | Krebs cycle and oxidative phosphorylation | Cells oxidise acetyl-CoA to CO₂, and use the resulting electron flow to pump protons and make ATP.
biology | Epigenetic inheritance | Gene expression states can be inherited through cell division without changes in DNA sequence.
biology | Cell cycle and apoptosis | Cells divide through regulated checkpoints and can trigger programmed death.
earth_science | Milankovitch cycles | Periodic changes in Earth's orbit and tilt pace glacial–interglacial cycles.
earth_science | Carbon cycle | Carbon moves among atmosphere, oceans, biosphere and rocks on timescales from years to millions of years.
earth_science | Water cycle | Water circulates by evaporation, condensation, precipitation and runoff, powered by sunlight.
earth_science | Thermohaline circulation | Density differences from temperature and salinity drive a global ocean conveyor.
earth_science | Coriolis effect | In a rotating frame moving bodies are deflected, shaping winds, currents and cyclones.
earth_science | Wilson cycle | Ocean basins open and close cyclically as supercontinents assemble and break apart.
astronomy | Hertzsprung-Russell diagram | Stars occupy distinct luminosity–temperature regions reflecting mass and evolutionary stage.
astronomy | Cosmic microwave background | Relic black-body radiation at 2.7255 K from recombination ~380,000 years after the Big Bang.
astronomy | Cosmic inflation | A brief early epoch of exponential expansion explains flatness, horizon uniformity and the seed fluctuations.
astronomy | Dark matter evidence | Galaxy rotation curves, lensing, cluster dynamics and the CMB require ~5× more non-luminous than baryonic matter.
astronomy | Accelerating expansion | Supernova distances show cosmic expansion is accelerating, attributed to dark energy.
astronomy | Exoplanets | Thousands of planets orbit other stars, detected by transits, radial velocities, imaging and microlensing.
mathematics | Central limit theorem | Sums of many independent finite-variance variables tend to a normal distribution.
mathematics | Law of large numbers | Sample averages converge to the expected value as sample size grows.
mathematics | Fundamental theorem of algebra | Every non-constant polynomial has a complex root.
mathematics | Fundamental theorem of arithmetic | Every integer > 1 factors uniquely into primes.
mathematics | Cantor's diagonal argument | The real numbers are uncountable: no list can contain them all.
mathematics | Halting problem | No algorithm decides for every program whether it halts.
mathematics | Brouwer fixed-point theorem | Every continuous map of a closed ball to itself has a fixed point.
mathematics | Nash equilibrium existence | Every finite game has an equilibrium in mixed strategies.
mathematics | Kolmogorov axioms | Probability is a non-negative, normalised, countably additive measure.
mathematics | Pigeonhole principle | Placing n+1 objects in n boxes puts two objects in one box.
information | Landauer's principle | Erasing one bit of information dissipates at least k_B T ln 2 of heat.
information | Nyquist-Shannon sampling theorem | A band-limited signal is fully reconstructed from samples taken at more than twice its highest frequency.
information | Shannon's channel coding theorem | Reliable communication is possible at any rate below channel capacity, and impossible above it.
"""

FRONTIER_EXT = """
physics | Origin and scale of neutrino masses | q:mass c:hbar c:c q:energy
physics | Hubble tension: early- vs late-universe expansion rate disagree | q:hubble_constant c:H_0 q:distance q:redshift
physics | Muon g-2 anomaly and physics beyond the Standard Model | c:m_mu q:magnetic_moment q:g_factor
physics | Turbulence: Navier-Stokes existence and smoothness | q:viscosity q:reynolds_number q:velocity q:density
physics | Arrow of time: why entropy was low at the Big Bang | q:entropy c:k_B q:temperature
physics | Origin of ultra-high-energy cosmic rays | q:energy q:magnetic_field q:charge
astronomy | Solar coronal heating problem | q:temperature q:magnetic_field q:power
astronomy | Origin of fast radio bursts | q:frequency q:luminosity q:distance
astronomy | Cosmic lithium problem | q:number_density q:temperature q:time
biology | Function of sleep | q:metabolic_rate q:time q:membrane_potential
biology | Triggers of the Cambrian explosion | q:population q:growth_rate q:time
chemistry | Room-temperature superconductivity | q:resistance q:temperature q:fermi_energy
"""
