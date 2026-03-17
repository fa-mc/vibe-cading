import sys
import math
import importlib

def analyze_profile(pts, tolerance=-0.01):
    print(f"Analyzing {len(pts)} points...")
    prev_th = None
    backward_count = 0
    for i, p in enumerate(pts):
        th = math.degrees(math.atan2(p[1], p[0]))
        # Unwrap negative values for smooth transition
        while prev_th is not None and th - prev_th < -180:
            th += 360
        while prev_th is not None and th - prev_th > 180:
            th -= 360

        if prev_th is not None:
            dth = th - prev_th
            if dth < tolerance:
                print(f"❌ BACKWARD LOOP DETECTED: index {i}, th: {prev_th:.2f}° -> {th:.2f}° (Δ={dth:.2f}°, r={math.hypot(p[0], p[1]):.2f})")
                backward_count += 1
        prev_th = th
    
    if backward_count == 0:
        print("✅ SUCCESS: Profile is strictly monotonic in polar angle (no backward hooks).")
    else:
        print(f"❌ FAILURE: {backward_count} backward sequence(s) found. This will create jagged geometric hooks.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_polar_monotonicity.py models.module.ClassName._method")
        sys.exit(1)
        
    target = sys.argv[1]
    module_path, class_name, method_name = target.rsplit(".", 2)
    
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        obj = cls()
        pts = getattr(obj, method_name)()
        analyze_profile(pts)
    except Exception as e:
        print(f"Error loading {target}: {e}")
        sys.exit(1)
