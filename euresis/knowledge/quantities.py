"""Canonical physical quantities: id | human name | SI dimension."""

_TABLE = """
mass | mass | M
mass1 | mass of body 1 | M
mass2 | mass of body 2 | M
length | length | L
distance | distance / separation | L
radius | radius | L
height | height | L
displacement | displacement | L
wavelength | wavelength | L
area | area | L2
volume | volume | L3
time | time | T
period | period | T
half_life | half-life | T
mean_lifetime | mean lifetime | T
time_constant | time constant | T
frequency | frequency | T-1
angular_frequency | angular frequency | T-1
decay_constant | decay constant | T-1
rate_constant | first-order rate constant | T-1
velocity | velocity | L T-1
initial_velocity | initial velocity | L T-1
final_velocity | final velocity | L T-1
escape_velocity | escape velocity | L T-1
orbital_velocity | orbital velocity | L T-1
wave_speed | wave speed | L T-1
speed_of_sound | speed of sound | L T-1
acceleration | acceleration | L T-2
gravitational_acceleration | gravitational field strength | L T-2
centripetal_acceleration | centripetal acceleration | L T-2
angular_velocity | angular velocity | T-1
angular_acceleration | angular acceleration | T-2
angle | angle | 1
force | force | M L T-2
weight | weight | M L T-2
normal_force | normal force | M L T-2
friction_force | friction force | M L T-2
tension | tension | M L T-2
buoyant_force | buoyant force | M L T-2
drag_force | drag force | M L T-2
spring_constant | spring constant | M T-2
friction_coefficient | coefficient of friction | 1
drag_coefficient | drag coefficient | 1
momentum | momentum | M L T-1
impulse | impulse | M L T-1
energy | energy | M L2 T-2
kinetic_energy | kinetic energy | M L2 T-2
potential_energy | potential energy | M L2 T-2
work | work | M L2 T-2
heat | heat | M L2 T-2
internal_energy | internal energy | M L2 T-2
rest_energy | rest energy | M L2 T-2
photon_energy | photon energy | M L2 T-2
binding_energy | binding energy | M L2 T-2
activation_energy | activation energy (per mole) | M L2 T-2 N-1
gibbs_energy | Gibbs free energy (per mole) | M L2 T-2 N-1
enthalpy | enthalpy (per mole) | M L2 T-2 N-1
molar_entropy | molar entropy | M L2 T-2 K-1 N-1
work_function | work function | M L2 T-2
power | power | M L2 T-3
intensity | intensity | M T-3
torque | torque | M L2 T-2
moment_of_inertia | moment of inertia | M L2
angular_momentum | angular momentum | M L2 T-1
pressure | pressure | M L-1 T-2
stress | stress | M L-1 T-2
strain | strain | 1
youngs_modulus | Young's modulus | M L-1 T-2
bulk_modulus | bulk modulus | M L-1 T-2
density | density | M L-3
linear_density | linear mass density | M L-1
viscosity | dynamic viscosity | M L-1 T-1
surface_tension | surface tension | M T-2
flow_rate | volumetric flow rate | L3 T-1
reynolds_number | Reynolds number | 1
temperature | temperature | K
temperature_hot | hot reservoir temperature | K
temperature_cold | cold reservoir temperature | K
temperature_change | temperature change | K
entropy | entropy | M L2 T-2 K-1
entropy_change | entropy change | M L2 T-2 K-1
heat_capacity | heat capacity | M L2 T-2 K-1
specific_heat | specific heat capacity | L2 T-2 K-1
latent_heat | specific latent heat | L2 T-2
thermal_conductivity | thermal conductivity | M L T-3 K-1
heat_flow | heat flow rate | M L2 T-3
efficiency | efficiency | 1
heat_capacity_ratio | heat capacity ratio | 1
emissivity | emissivity | 1
amount | amount of substance | N
molar_mass | molar mass | M N-1
concentration | molar concentration | N L-3
number | number of particles | 1
number_density | number density | L-3
charge | electric charge | I T
charge1 | charge 1 | I T
charge2 | charge 2 | I T
current | electric current | I
voltage | voltage / potential difference | M L2 T-3 I-1
emf | electromotive force | M L2 T-3 I-1
electric_potential | electric potential | M L2 T-3 I-1
gravitational_potential | gravitational potential | L2 T-2
resistance | resistance | M L2 T-3 I-2
resistivity | resistivity | M L3 T-3 I-2
conductance | conductance | M-1 L-2 T3 I2
capacitance | capacitance | M-1 L-2 T4 I2
inductance | inductance | M L2 T-2 I-2
electric_field | electric field | M L T-3 I-1
magnetic_field | magnetic flux density | M T-2 I-1
magnetic_flux | magnetic flux | M L2 T-2 I-1
electric_flux | electric flux | M L3 T-3 I-1
current_density | current density | I L-2
charge_density | volume charge density | I T L-3
energy_density | energy density | M L-1 T-2
turns | number of turns | 1
turns_per_length | turns per unit length | L-1
relative_permittivity | relative permittivity | 1
refractive_index | refractive index | 1
refractive_index1 | refractive index of medium 1 | 1
refractive_index2 | refractive index of medium 2 | 1
angle1 | angle of incidence | 1
angle2 | angle of refraction | 1
focal_length | focal length | L
object_distance | object distance | L
image_distance | image distance | L
magnification | magnification | 1
slit_separation | slit separation | L
order | diffraction order | 1
luminosity | luminosity | M L2 T-3
flux | radiant flux density | M T-3
redshift | redshift | 1
hubble_constant | Hubble parameter | T-1
recession_velocity | recession velocity | L T-1
schwarzschild_radius | Schwarzschild radius | L
semi_major_axis | semi-major axis | L
lorentz_factor | Lorentz factor | 1
proper_time | proper time | T
proper_length | proper length | L
de_broglie_wavelength | de Broglie wavelength | L
position_uncertainty | position uncertainty | L
momentum_uncertainty | momentum uncertainty | M L T-1
energy_uncertainty | energy uncertainty | M L2 T-2
time_uncertainty | time uncertainty | T
quantum_number | principal quantum number | 1
energy_level | energy level | M L2 T-2
peak_wavelength | peak wavelength | L
atomic_number | atomic number | 1
mass_number | mass number | 1
activity | radioactive activity | T-1
initial_number | initial number of nuclei | 1
mass_defect | mass defect | M
ph | pH | 1
poh | pOH | 1
hydrogen_concentration | hydrogen ion concentration (in mol/L) | 1
hydroxide_concentration | hydroxide ion concentration (in mol/L) | 1
equilibrium_constant | equilibrium constant | 1
reaction_quotient | reaction quotient | 1
cell_potential | cell potential | M L2 T-3 I-1
standard_cell_potential | standard cell potential | M L2 T-3 I-1
electrons_transferred | electrons transferred | 1
pka | pKa | 1
acid_ratio | [A-]/[HA] ratio | 1
pre_exponential | Arrhenius pre-exponential factor | T-1
osmotic_pressure | osmotic pressure | M L-1 T-2
vant_hoff_factor | van 't Hoff factor | 1
molality | molality | N M-1
freezing_point_depression | freezing point depression | K
cryoscopic_constant | cryoscopic constant | K M N-1
absorbance | absorbance | 1
molar_absorptivity | molar absorptivity | L2 N-1
path_length | path length | L
partial_pressure | partial pressure | M L-1 T-2
henry_constant | Henry's law constant (solubility) | N M-1 L-2 T2
mole_fraction | mole fraction | 1
vapor_pressure_pure | vapour pressure of pure solvent | M L-1 T-2
population | population size | 1
population_rate | population growth rate | T-1
initial_population | initial population | 1
growth_rate | intrinsic growth rate | T-1
carrying_capacity | carrying capacity | 1
allele_p | dominant allele frequency | 1
allele_q | recessive allele frequency | 1
reaction_velocity | reaction velocity | N L-3 T-1
max_velocity | maximum reaction velocity | N L-3 T-1
substrate_concentration | substrate concentration | N L-3
michaelis_constant | Michaelis constant | N L-3
hill_coefficient | Hill coefficient | 1
fraction_bound | fraction of sites bound | 1
dissociation_constant | dissociation constant | N L-3
membrane_potential | membrane potential | M L2 T-3 I-1
ion_charge | ion valence | 1
conc_outside | ion concentration outside | N L-3
conc_inside | ion concentration inside | N L-3
diffusion_coefficient | diffusion coefficient | L2 T-1
mean_squared_displacement | mean squared displacement | L2
basic_reproduction_number | basic reproduction number | 1
herd_immunity_threshold | herd immunity threshold | 1
transmission_rate | transmission rate | T-1
recovery_rate | recovery rate | T-1
generation_time | generation (doubling) time | T
metabolic_rate | metabolic rate | M L2 T-3
bmr_coefficient | Kleiber coefficient | M0.25 L2 T-3
heritability | narrow-sense heritability | 1
selection_differential | selection differential | 1
response_to_selection | response to selection | 1
magnitude | apparent magnitude | 1
absolute_magnitude | absolute magnitude | 1
distance_parsec | distance in parsecs | 1
parallax_arcsec | parallax in arcseconds | 1
seismic_moment | seismic moment | M L2 T-2
seismic_moment_value | seismic moment (numeric value in N·m) | 1
moment_magnitude | moment magnitude | 1
depth | depth | L
lapse_rate | lapse rate | K L-1
scale_height | atmospheric scale height | L
information | information (bits) | 1
probability | probability | 1
shannon_entropy | Shannon entropy (bits) | 1
"""

QUANTITIES: dict[str, tuple[str, str]] = {}
for _line in _TABLE.strip().splitlines():
    _id, _name, _dim = (s.strip() for s in _line.split("|"))
    QUANTITIES[_id] = (_name, _dim)
