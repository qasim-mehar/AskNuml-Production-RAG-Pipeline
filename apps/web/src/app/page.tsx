import Link from "next/link";

/** Static landing page reporting system health (no fetching). */
export default function Home() {
  return (
    <main>
      <h1>uni-rag</h1>
      <p>System status: healthy</p>
      <nav aria-label="Main">
        <ul>
          <li>
            <Link href="/chat">Cited chat</Link>
          </li>
          <li>
            <Link href="/papers">Past-paper finder</Link>
          </li>
        </ul>
      </nav>
    </main>
  );
}
