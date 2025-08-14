import argparse
import cv2, numpy as np, glob, os

def estimate_overlaps(folder, pattern, grid_width, grid_height,
                      layout="raster", direction="horizontal",
                      min_frac=0.06, max_frac=0.18, center_frac=0.7, slices=4):
    """
    Return {'overlap_x','overlap_y','width_px','height_px','n_used_x','n_used_y'}
    """
    files = sorted(glob.glob(os.path.join(folder, pattern)))
    if len(files) != grid_width * grid_height:
        raise ValueError("File count != grid_width*grid_height. Filter to ONE channel.")

    # map linear index -> (r,c) using layout + direction
    def idx_to_rc(k):
        if direction == "horizontal":  # row-major
            r, c = divmod(k, grid_width)
            if layout == "snake" and (r % 2 == 1): c = grid_width - 1 - c
        else:  # vertical: column-major
            c, r = divmod(k, grid_height)
            if layout == "snake" and (c % 2 == 1): r = grid_height - 1 - r
        return r, c

    # load grid
    imgs = [[None]*grid_width for _ in range(grid_height)]
    for k, f in enumerate(files):
        r, c = idx_to_rc(k)
        imgs[r][c] = cv2.imread(f, cv2.IMREAD_GRAYSCALE)
        if imgs[r][c] is None:
            raise RuntimeError(f"Cannot read {f}")
    H, W = imgs[0][0].shape

    def ncc(a,b):
        a=a.astype(np.float32); b=b.astype(np.float32)
        a-=a.mean(); b-=b.mean()
        d=np.sqrt((a*a).sum()*(b*b).sum()); 
        return 0.0 if d==0 else float((a*b).sum()/d)

    min_ox, max_ox = max(int(W*min_frac),16), int(W*max_frac)
    min_oy, max_oy = max(int(H*min_frac),16), int(H*max_frac)

    def best_overlap_horizontal(A, B):
        # central vertical band + multi-slice
        x0 = int(W*(1-center_frac)/2); x1 = W - x0
        bandA, bandB = A[:,x0:x1], B[:,x0:x1]
        w = bandA.shape[1]//slices
        os_px, qs = [], []
        for i in range(slices):
            xa, xb = i*w, bandA.shape[1] if i==slices-1 else (i+1)*w
            segA, segB = bandA[:,xa:xb], bandB[:,xa:xb]
            segA = segA - cv2.GaussianBlur(segA,(0,0),1)
            segB = segB - cv2.GaussianBlur(segB,(0,0),1)
            best_o, best_q = None, -1.0
            for o in range(min_ox, max_ox+1):
                q = ncc(segA[:,-o:], segB[:,:o])
                if q > best_q: best_q, best_o = q, o
            os_px.append(best_o); qs.append(best_q)
        return int(np.median(os_px)), float(np.median(qs))

    def best_overlap_vertical(A, B):
        y0 = int(H*(1-center_frac)/2); y1 = H - y0
        bandA, bandB = A[y0:y1,:], B[y0:y1,:]
        w = bandA.shape[1]//slices
        os_px, qs = [], []
        for i in range(slices):
            xa, xb = i*w, bandA.shape[1] if i==slices-1 else (i+1)*w
            segA, segB = bandA[:,xa:xb], bandB[:,xa:xb]
            segA = segA - cv2.GaussianBlur(segA,(0,0),1)
            segB = segB - cv2.GaussianBlur(segB,(0,0),1)
            best_o, best_q = None, -1.0
            for o in range(min_oy, max_oy+1):
                q = ncc(segA[-o:,:], segB[:o,:])
                if q > best_q: best_q, best_o = q, o
            os_px.append(best_o); qs.append(best_q)
        return int(np.median(os_px)), float(np.median(qs))

    # collect per-pair estimates
    ox_fracs, oy_fracs, qx, qy = [], [], [], []
    # horizontal neighbors
    for r in range(grid_height):
        for c in range(grid_width-1):
            o_px, q = best_overlap_horizontal(imgs[r][c], imgs[r][c+1])
            ox_fracs.append(o_px/W); qx.append(q)
    # vertical neighbors
    for r in range(grid_height-1):
        for c in range(grid_width):
            o_px, q = best_overlap_vertical(imgs[r][c], imgs[r+1][c])
            oy_fracs.append(o_px/H); qy.append(q)

    # robust aggregation: keep middle 60% by correlation
    def robust_median(vals, qs):
        if not vals: return None, 0
        qs = np.array(qs); vals = np.array(vals)
        lo, hi = np.quantile(qs, [0.2, 0.8])
        keep = (qs>=lo) & (qs<=hi)
        used = int(keep.sum())
        return float(np.median(vals[keep])) if used>0 else float(np.median(vals)), used

    ox, nx = robust_median(ox_fracs, qx)
    oy, ny = robust_median(oy_fracs, qy)

    return {"overlap_x": ox, "overlap_y": oy,
            "width_px": W, "height_px": H,
            "n_used_x": nx, "n_used_y": ny}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--pattern", default="*.tif")
    ap.add_argument("--grid-width", type=int, required=True)   # columns
    ap.add_argument("--grid-height", type=int, required=True)  # rows
    ap.add_argument("--pixel-size", type=float, default=None)  # optional, µm/px
    args = ap.parse_args()

    res = estimate_overlaps(args.folder, args.pattern, args.grid_width, args.grid_height)
    ox, oy = res["overlap_x"], res["overlap_y"]
    # pick a single value for Ashlar (safer to use the smaller one)
    ov = min([v for v in [ox, oy] if v is not None])

    print(f"Estimated overlap_x={ox:.4f}  overlap_y={oy:.4f}")
    print(f"Recommended overlap={ov:.4f}")
    if args.pixel_size is not None:
        print("\nAshlar fileseries snippet:")
        print(f'overlap={ov:.3f}|pixel_size={args.pixel_size}')
