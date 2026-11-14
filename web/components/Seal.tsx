export function Seal({ size = 48 }: { size?: number }) {
  return (
    <div
      className="seal"
      style={{ width: size, height: size, fontSize: size * 0.46 }}
      aria-hidden
    >
      巷
    </div>
  );
}
