// Entrega à página da área interna a URL do projeto e a chave pública (anon), lidas do ambiente do Supabase,
// para que nenhuma chave fique escrita no repositório. Sem JWT: é o primeiro passo antes do login.
Deno.serve(() =>
  new Response(JSON.stringify({ url: Deno.env.get("SUPABASE_URL"), chave: Deno.env.get("SUPABASE_ANON_KEY") }), {
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*", "Cache-Control": "max-age=300" },
  })
);
