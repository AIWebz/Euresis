// Computer-assisted existence proof for symmetric periodic orbits of the planar
// equal-mass three-body problem (G = m = 1), using kv (validated ODE solver,
// interval arithmetic, Krawczyk test).
//
// Unknowns x = (p1, p2, tau).  Initial state (Fix of the reversor R):
//   r1 = (-1,0), r2 = (1,0), r3 = (0,0), v1 = v2 = (p1,p2), v3 = -2 (p1,p2).
// Residual  F(x) = ( x3(tau), y3(tau), (v1 - v2)(tau) . r1(tau) ).
// If F has a zero then (with L = 0, P = 0 conserved) z(tau) lies in Fix(R) as
// well, hence the solution is periodic with period 2*tau.  krawczyk_approx
// proves that a unique zero exists inside an explicit interval box; the
// validated integration also proves the motion is collision-free on [0, tau].
#include <iostream>
#include <cstdlib>
#include <sstream>
#include <vector>
#include <kv/strobomap.hpp>
#include <kv/newton.hpp>
#include <kv/kraw-approx.hpp>

namespace ub = boost::numeric::ublas;
typedef kv::interval<double> itv;

struct ThreeBody {
	template <class T> ub::vector<T> operator() (const ub::vector<T>& z, T t) {
		using std::sqrt;
		ub::vector<T> d(12);
		for (int i = 0; i < 6; i++) d(i) = z(6 + i);
		for (int i = 6; i < 12; i++) d(i) = z(0) * 0.;
		for (int i = 0; i < 3; i++) for (int j = i + 1; j < 3; j++) {
			T dx = z(2*j) - z(2*i), dy = z(2*j+1) - z(2*i+1);
			T r = sqrt(dx*dx + dy*dy);
			T r3 = r * r * r;
			T ax = dx / r3, ay = dy / r3;
			d(6+2*i) += ax; d(7+2*i) += ay;
			d(6+2*j) -= ax; d(7+2*j) -= ay;
		}
		return d;
	}
};

template <class T> ub::vector<T> init_state(const T& p1, const T& p2) {
	ub::vector<T> z(12);
	T zero = p1 * 0.;
	z(0) = zero - 1.; z(1) = zero; z(2) = zero + 1.; z(3) = zero; z(4) = zero; z(5) = zero;
	z(6) = p1; z(7) = p2; z(8) = p1; z(9) = p2; z(10) = -2. * p1; z(11) = -2. * p2;
	return z;
}

template <class T> ub::vector<T> residual(const ub::vector<T>& y) {
	ub::vector<T> r(3);
	r(0) = y(4); r(1) = y(5);
	r(2) = (y(6) - y(8)) * y(0) + (y(7) - y(9)) * y(1);
	return r;
}

struct HalfOrbit {
	ThreeBody f;
	kv::ode_param<double> p;
	HalfOrbit(kv::ode_param<double> p) : p(p) {}

	ub::vector<double> operator() (const ub::vector<double>& x) {
		kv::StroboMap<ThreeBody, double> st(f, itv(0.), itv(x(2)), p);
		return residual(st(init_state(x(0), x(1))));
	}
	ub::vector< kv::autodif<double> > operator() (const ub::vector< kv::autodif<double> >& x) {
		itv t = itv(x(2).v);
		kv::StroboMap<ThreeBody, double> st(f, itv(0.), t, p);
		ub::vector< kv::autodif<double> > y = st(init_state(x(0), x(1)));
		ub::vector<double> y2(12);
		for (int i = 0; i < 12; i++) y2(i) = y(i).v;
		ub::vector<double> dzdt = f(y2, mid(t));
		for (int i = 0; i < 12; i++) y(i).d += dzdt(i) * x(2).d;
		return residual(y);
	}
	ub::vector<itv> operator() (const ub::vector<itv>& x) {
		kv::StroboMap<ThreeBody, double> st(f, itv(0.), x(2), p);
		return residual(st(init_state(x(0), x(1))));
	}
	ub::vector< kv::autodif<itv> > operator() (const ub::vector< kv::autodif<itv> >& x) {
		itv t = x(2).v;
		kv::StroboMap<ThreeBody, double> st(f, itv(0.), t, p);
		ub::vector< kv::autodif<itv> > y = st(init_state(x(0), x(1)));
		ub::vector<itv> y2(12);
		for (int i = 0; i < 12; i++) y2(i) = y(i).v;
		ub::vector<itv> dzdt = f(y2, t);
		for (int i = 0; i < 12; i++) y(i).d += dzdt(i) * x(2).d;
		return residual(y);
	}
};

int main(int argc, char** argv) {
	if (argc < 4) { std::cerr << "usage: p1 p2 tau [order]\n"; return 2; }
	std::cout.precision(17);
	int order = argc > 4 ? std::atoi(argv[4]) : 24;
	kv::ode_param<double> prm;
	prm.set_order(order);
	HalfOrbit F(prm);
	ub::vector<double> x(3);
	x(0) = std::atof(argv[1]); x(1) = std::atof(argv[2]); x(2) = std::atof(argv[3]);
	ub::vector<itv> ix;
	kv::newton(F, x);
	std::cout << "newton: " << x << "\n";
	std::cout << "residual: " << F(x) << "\n";
	// Krawczyk test  K(I) = c - R F(c) + (Id - R F'(I)) (I - c)  subset int(I)  =>  unique zero in I.
	// R is any (approximate) inverse; everything else is evaluated rigorously.
	ub::vector<itv> C(3), fc, fi, K, I(3);
	ub::matrix<itv> fdc, fdi, M;
	ub::matrix<double> R;
	for (int i = 0; i < 3; i++) C(i) = itv(x(i));
	kv::autodif<itv>::split(F(kv::autodif<itv>::init(C)), fc, fdc);
	if (!kv::invert(mid(fdc), R)) { std::cout << "singular Jacobian\n"; return 1; }
	std::cout << "F(c) enclosure: " << fc << "\n";
	if (getenv("KV_VERBOSE")) { std::cout << "F'(c): " << fdc << "\nR: " << R << "\n"; }
	ub::vector<itv> Rfc = prod(R, fc);
	bool ok = false;
	std::vector<double> radii = {1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6};
	if (getenv("KV_RADII")) { radii.clear(); std::stringstream ss(getenv("KV_RADII")); double v; while (ss >> v) radii.push_back(v); }
	for (double rad : radii) {
		for (int i = 0; i < 3; i++) I(i) = C(i) + rad * itv(-1., 1.);
		try {
			kv::autodif<itv>::split(F(kv::autodif<itv>::init(I)), fi, fdi);
		} catch (std::exception& e) { std::cout << "radius " << rad << ": integration failed (" << e.what() << ")\n"; break; }
		M = ub::identity_matrix<itv>(3);
		M -= prod(R, fdi);
		K = C - Rfc + prod(M, I - C);
		double mnorm = 0; for (int i = 0; i < 3; i++) { double row = 0; for (int j = 0; j < 3; j++) row += mag(M(i, j)); mnorm = std::max(mnorm, row); }
		ok = kv::proper_subset(K, I);
		if (getenv("KV_VERBOSE")) std::cout << "F'(I): " << fdi << "\nM: " << M << "\n";
		std::cout << "radius " << rad << ": ||Id - R F'(I)||_inf <= " << mnorm << (ok ? "  -> K(I) inside I" : "  -> not contained") << "\n" << std::flush;
		if (ok) { ix = K; break; }
	}
	if (ok) {
		std::cout << "PROVED: unique zero in box\n";
		for (int i = 0; i < 3; i++) std::cout << "  x" << i << " in " << ix(i) << "  width " << width(ix(i)) << "\n";
		std::cout << "  period 2*tau in " << 2. * ix(2) << "\n";
	} else {
		std::cout << "NOT PROVED (Krawczyk test failed)\n";
	}
	return ok ? 0 : 1;
}
