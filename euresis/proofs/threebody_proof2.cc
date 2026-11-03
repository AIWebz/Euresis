// Computer-assisted existence proof for symmetric periodic orbits of the planar
// equal-mass three-body problem (G = m = 1).  Version 2: variational equations
// are integrated *inside* the validated (affine-arithmetic) ODE solve, which
// avoids the wrapping blow-up of interval-matrix products on long orbits, and
// [0, tau] is split into N segments whose solution enclosures are chained.
//
// Unknowns x = (p1, p2, tau).  Initial state (in Fix of the reversor R):
//   r1 = (-1,0), r2 = (1,0), r3 = (0,0), v1 = v2 = (p1,p2), v3 = -2 (p1,p2).
// F(x) = ( x3(tau), y3(tau), (v1 - v2)(tau) . r1(tau) ).
// F(x) = 0  =>  z(tau) in Fix(R) (L = P = 0 are conserved)  =>  period 2 tau.
// Krawczyk:  K(I) = c - R F(c) + (Id - R F'(I)) (I - c) strictly inside I
//   =>  F has exactly one zero in I.  All of F(c), F'(I) are rigorous enclosures.
#include <iostream>
#include <sstream>
#include <vector>
#include <cstdlib>
#include <kv/ode-maffine.hpp>
#include <kv/ode-nv.hpp>
#include <kv/ode-autodif-nv.hpp>
#include <kv/autodif.hpp>
#include <kv/matrix-inversion.hpp>
#include <kv/interval-vector.hpp>

namespace ub = boost::numeric::ublas;
typedef kv::interval<double> itv;

// state: z(0..11) = positions/velocities; z(12..35) = Phi (12 x 2, column major),
// Phi = dz/d(p1,p2).  Time is rescaled: s in [0,1], t = tau * s, so tau is a
// parameter of the vector field and no interval end time is needed.
// The last component is tau itself (d tau/ds = 0), so its dependency is tracked.
struct Extended {
	bool var;
	bool scaled;
	Extended(bool var, bool scaled = true) : var(var), scaled(scaled) {}
	template <class T> ub::vector<T> operator() (const ub::vector<T>& z, T t) {
		using std::sqrt;
		int n = var ? 36 : 12;
		ub::vector<T> d(z.size());
		T zero = z(0) * 0.;
		for (int i = 0; i < n; i++) d(i) = zero;
		for (int i = 0; i < 6; i++) d(i) = z(6 + i);
		for (int i = 0; i < 3; i++) for (int j = i + 1; j < 3; j++) {
			T dx = z(2*j) - z(2*i), dy = z(2*j+1) - z(2*i+1);
			T r2 = dx*dx + dy*dy;
			T r = sqrt(r2);
			T ir3 = 1. / (r2 * r);
			T ax = dx * ir3, ay = dy * ir3;
			d(6+2*i) += ax; d(7+2*i) += ay;
			d(6+2*j) -= ax; d(7+2*j) -= ay;
			if (var) {
				// D(d/|d|^3) = I/|d|^3 - 3 d d^T/|d|^5
				T ir5 = ir3 / r2;
				T a11 = ir3 - 3. * dx * dx * ir5, a12 = -3. * dx * dy * ir5, a22 = ir3 - 3. * dy * dy * ir5;
				for (int k = 0; k < 2; k++) {
					int o = 12 + 12 * k;
					T ddx = z(o + 2*j) - z(o + 2*i), ddy = z(o + 2*j+1) - z(o + 2*i+1);
					T gx = a11 * ddx + a12 * ddy, gy = a12 * ddx + a22 * ddy;
					d(o + 6+2*i) += gx; d(o + 7+2*i) += gy;
					d(o + 6+2*j) -= gx; d(o + 7+2*j) -= gy;
				}
				for (int k = 0; k < 2; k++) {
					int o = 12 + 12 * k;
					for (int m = 0; m < 6; m++) d(o + m) = z(o + 6 + m);
				}
			}
		}
		if (scaled) { for (int i = 0; i < n; i++) d(i) *= z(n); d(n) = zero; }
		return d;
	}
};

static int ORDER = 30;
static int NSEG = 1;

ub::vector<itv> init_state(itv p1, itv p2, itv tau, bool var) {
	ub::vector<itv> z(var ? 37 : 13);
	for (int i = 0; i < (int)z.size(); i++) z(i) = 0.;
	z(0) = -1.; z(2) = 1.;
	z(6) = p1; z(7) = p2; z(8) = p1; z(9) = p2; z(10) = -2. * p1; z(11) = -2. * p2;
	z(z.size() - 1) = tau;
	if (var) {
		z(12 + 6) = 1.; z(12 + 8) = 1.; z(12 + 10) = -2.;        // d/dp1
		z(24 + 7) = 1.; z(24 + 9) = 1.; z(24 + 11) = -2.;        // d/dp2
	}
	return z;
}

// rigorous enclosure of z(tau) for all p in (p1,p2), tau in tau (time s in [0,1])
ub::vector<itv> flow(itv p1, itv p2, itv tau, bool var) {
	Extended f(var);
	ub::vector<itv> z = init_state(p1, p2, tau, var);
	kv::ode_param<double> prm;
	prm.set_order(ORDER);
	ub::vector< kv::affine<double> > a = z;
	for (int k = 0; k < NSEG; k++) {
		itv s0 = itv(k) / NSEG, s1 = itv(k + 1) / NSEG;
		itv end = s1;
		int r = kv::odelong_maffine(f, a, s0, end, prm);
		if (r != 2) throw std::domain_error("validated integration failed");
	}
	return kv::to_interval(a);
}

ub::vector<itv> residual(const ub::vector<itv>& y) {
	ub::vector<itv> r(3);
	r(0) = y(4); r(1) = y(5);
	r(2) = (y(6) - y(8)) * y(0) + (y(7) - y(9)) * y(1);
	return r;
}

// Jacobian enclosure over the box from the 36-dim enclosure
ub::matrix<itv> jacobian(const ub::vector<itv>& y) {
	// dG/dz (3 x 12)
	ub::matrix<itv> DG(3, 12);
	for (int i = 0; i < 3; i++) for (int j = 0; j < 12; j++) DG(i, j) = 0.;
	DG(0, 4) = 1.; DG(1, 5) = 1.;
	DG(2, 0) = y(6) - y(8); DG(2, 1) = y(7) - y(9);
	DG(2, 6) = y(0); DG(2, 7) = y(1); DG(2, 8) = -y(0); DG(2, 9) = -y(1);
	// columns: dz/dp1, dz/dp2, dz/dtau = f(z) (physical time)
	ub::vector<itv> zz(12);
	for (int i = 0; i < 12; i++) zz(i) = y(i);
	Extended phys(false, false);
	ub::vector<itv> fz = phys(zz, itv(0.));
	ub::matrix<itv> J(3, 3);
	for (int i = 0; i < 3; i++) {
		itv s1(0.), s2(0.), s3(0.);
		for (int j = 0; j < 12; j++) {
			s1 += DG(i, j) * y(12 + j);
			s2 += DG(i, j) * y(24 + j);
			s3 += DG(i, j) * fz(j);
		}
		J(i, 0) = s1; J(i, 1) = s2; J(i, 2) = s3;
	}
	return J;
}

// approximate F and its Jacobian (double precision, NOT rigorous: only used for c and R)
void approx(const ub::vector<double>& c, ub::vector<double>& F, ub::matrix<double>& J) {
	typedef kv::autodif<double> ad;
	ub::vector<ad> x = ad::init(c);
	ub::vector<ad> z(13);
	ad zero = x(0) * 0.;
	for (int i = 0; i < 13; i++) z(i) = zero;
	z(0) = zero - 1.; z(2) = zero + 1.;
	z(6) = x(0); z(7) = x(1); z(8) = x(0); z(9) = x(1); z(10) = -2. * x(0); z(11) = -2. * x(1);
	z(12) = x(2);
	Extended f(false);
	kv::ode_param<double> prm;
	prm.set_order(ORDER);
	kv::odelong_nv(f, z, 0., 1., prm);
	ub::vector<ad> r(3);
	r(0) = z(4); r(1) = z(5);
	r(2) = (z(6) - z(8)) * z(0) + (z(7) - z(9)) * z(1);
	ad::split(r, F, J);
}

int main(int argc, char** argv) {
	if (argc < 4) { std::cerr << "usage: p1 p2 tau [order] [nseg]\n"; return 2; }
	std::cout.precision(17);
	if (argc > 4) ORDER = std::atoi(argv[4]);
	if (argc > 5) NSEG = std::atoi(argv[5]);
	ub::vector<double> c(3);
	c(0) = std::atof(argv[1]); c(1) = std::atof(argv[2]); c(2) = std::atof(argv[3]);

	// Newton refinement (approximate)
	ub::vector<double> Fa; ub::matrix<double> Ja, R;
	for (int it = 0; it < 6; it++) {
		approx(c, Fa, Ja);
		if (!kv::invert(Ja, R)) { std::cout << "singular\n"; return 1; }
		c -= prod(R, Fa);
		std::cout << "newton " << it << ": " << c << "  F ~ " << Fa << "\n" << std::flush;
	}
	approx(c, Fa, Ja);
	kv::invert(Ja, R);
	// rigorous enclosure of F at the (floating-point) centre
	ub::vector<itv> C(3);
	for (int i = 0; i < 3; i++) C(i) = c(i);
	ub::vector<itv> fc = residual(flow(C(0), C(1), C(2), false));
	std::cout << "F(c) enclosure: " << fc << "\n";
	ub::vector<itv> Rfc = prod(R, fc);

	std::vector<double> radii = {1e-9, 1e-8, 1e-10, 1e-7};
	if (getenv("KV_RADII")) { radii.clear(); std::stringstream ss(getenv("KV_RADII")); double v; while (ss >> v) radii.push_back(v); }
	bool ok = false;
	ub::vector<itv> K, I(3);
	for (double rad : radii) {
		for (int i = 0; i < 3; i++) I(i) = C(i) + rad * itv(-1., 1.);
		ub::matrix<itv> JI;
		try {
			JI = jacobian(flow(I(0), I(1), I(2), true));
		} catch (std::exception& e) { std::cout << "radius " << rad << ": " << e.what() << "\n"; continue; }
		ub::matrix<itv> M = ub::identity_matrix<itv>(3);
		M -= prod(R, JI);
		K = C - Rfc + prod(M, I - C);
		double mnorm = 0;
		for (int i = 0; i < 3; i++) { double row = 0; for (int j = 0; j < 3; j++) row += mag(M(i, j)); mnorm = std::max(mnorm, row); }
		ok = kv::proper_subset(K, I);
		std::cout << "radius " << rad << ": ||Id - R F'(I)||_inf <= " << mnorm << (ok ? "  -> K(I) inside I" : "  -> not contained") << "\n" << std::flush;
		if (getenv("KV_VERBOSE")) std::cout << "F'(I): " << JI << "\n";
		if (ok) break;
	}
	if (ok) {
		std::cout << "PROVED: unique zero in box\n";
		for (int i = 0; i < 3; i++) std::cout << "  x" << i << " in " << K(i) << "  width " << width(K(i)) << "\n";
		std::cout << "  period 2*tau in " << 2. * K(2) << "\n";
	} else {
		std::cout << "NOT PROVED (Krawczyk test failed)\n";
	}
	return ok ? 0 : 1;
}
