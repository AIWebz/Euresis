"""Open problems at the frontier of science — what Euresis explores toward.

domain | problem | concepts it touches (quantities q:, constants c:)
"""

FRONTIER = """
physics | Quantum gravity: unify general relativity with quantum mechanics | c:G c:hbar c:c c:h
physics | Nature of dark matter (~27% of the universe's energy budget) | c:G q:mass q:orbital_velocity q:radius
physics | Nature of dark energy and the cosmological constant problem | q:hubble_constant c:H_0 c:G q:energy_density
physics | Matter–antimatter asymmetry of the universe | q:number q:energy c:c
physics | Origin of particle masses and the hierarchy problem | q:mass c:hbar c:c c:G
physics | Measurement problem in quantum mechanics | c:hbar q:probability q:position_uncertainty
physics | Is the fine-structure constant truly constant? | c:alpha c:e c:hbar c:c c:epsilon_0
physics | High-temperature superconductivity mechanism | q:resistance q:temperature q:current_density
chemistry | Predicting protein folding and reaction rates from first principles | q:activation_energy q:rate_constant q:gibbs_energy
chemistry | Room-temperature catalysis for nitrogen fixation and CO2 reduction | q:activation_energy q:rate_constant q:pre_exponential
biology | Origin of life: from chemistry to self-replication | q:gibbs_energy q:rate_constant q:population
biology | Theory of ageing and limits of lifespan | q:metabolic_rate q:mass q:mean_lifetime
biology | How consciousness arises from neural activity | q:membrane_potential q:information
earth_science | Predicting earthquakes | q:seismic_moment q:stress q:strain
earth_science | Climate sensitivity to CO2 doubling | q:temperature q:power q:emissivity c:sigma
astronomy | Information paradox of black holes | q:schwarzschild_radius q:entropy c:G c:hbar c:k_B
mathematics | Riemann hypothesis and the distribution of primes | q:information q:probability
information | P vs NP: limits of efficient computation | q:information q:energy c:k_B
"""


def load():
    out = []
    for line in FRONTIER.strip().splitlines():
        dom, prob, tags = (p.strip() for p in line.split("|"))
        out.append((dom, prob, tags.split()))
    return out
