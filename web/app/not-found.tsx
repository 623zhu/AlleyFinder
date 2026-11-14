import Link from "next/link";
import { Seal } from "@/components/Seal";

export default function NotFound() {
  return (
    <main className="shell empty">
      <Seal />
      <p className="serif title" style={{ fontSize: 32 }}>
        巷探
      </p>
      <p className="tagline">这条巷子还没探到</p>
      <Link href="/">回起点</Link>
    </main>
  );
}
