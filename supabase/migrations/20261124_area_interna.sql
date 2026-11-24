-- Área interna: codificação humana das publicações do núcleo e concordância (kappa de Cohen).
-- Pedido do responsável em 24/11/2026 (17h39): área interna com base na estrutura já usada pelo responsável;
-- escopo escolhido: "Codificação e kappa". Projeto Supabase próprio (odi-influenciadoras, sa-east-1).
--
-- Quem entra: convidado pelo responsável (auth.users + public.pesquisadores), ativo e com o termo aceito.
-- Cegueira: cada codificador lê e grava só as próprias codificações; os outros só aparecem como agregado (kappa).
-- O responsável (papel 'responsavel') vê as divergências e grava a decisão final (terceiro codificador).
-- As unidades são públicas (posts das quatro e transcrições já publicadas); nenhum dado de terceiro entra aqui.

create schema if not exists odi_interno;
revoke all on schema odi_interno from public, anon;
grant usage on schema odi_interno to authenticated;

create table if not exists public.pesquisadores (
  user_id uuid primary key references auth.users(id) on delete cascade,
  nome text,
  papel text not null default 'codificador' check (papel in ('codificador', 'responsavel')),
  ativo boolean not null default true,
  termo_aceito_em timestamptz,
  criado_em timestamptz not null default now()
);

create table if not exists public.unidades (
  id text primary key,                 -- '<rede>:<post_id>'
  ator_id text not null,
  rede text not null check (rede in ('youtube', 'instagram', 'tiktok', 'x')),
  publicado_em timestamptz,
  tipo text,
  url text,
  texto text,                          -- legenda (Instagram, TikTok) ou título (YouTube)
  transcricao text,                    -- Whisper; null quando não houve áudio ou a transcrição falhou
  transcricao_status text,
  ordem text not null,                 -- md5(id): ordem fixa de apresentação, igual para todos
  carregado_em timestamptz not null default now()
);

create table if not exists public.codificacoes (
  unidade_id text not null references public.unidades(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  mencao text check (mencao in ('acordo', 'gaza', 'nao_politica', 'sem_relacao')),
  posicao text check (posicao in ('favoravel', 'cetica', 'contraria', 'informativa', 'humanitaria', 'nao_se_aplica')),
  enquadramento text check (enquadramento in ('religioso', 'politico', 'humanitario', 'identitario', 'denuncia', 'nenhum')),
  formato text check (formato in ('fala_propria', 'repost', 'legenda', 'convite', 'outro')),
  obs text,
  atualizado_em timestamptz not null default now(),
  primary key (unidade_id, user_id),
  check (posicao is null or mencao is null or (mencao in ('acordo', 'gaza')) = (posicao <> 'nao_se_aplica'))
);

create table if not exists public.decisoes (
  unidade_id text not null references public.unidades(id) on delete cascade,
  dimensao text not null check (dimensao in ('mencao', 'posicao', 'enquadramento', 'formato')),
  valor text not null,
  decidido_por uuid not null default auth.uid() references auth.users(id),
  decidido_em timestamptz not null default now(),
  primary key (unidade_id, dimensao)
);

create table if not exists public.acessos (
  id bigint generated always as identity primary key,
  user_id uuid not null default auth.uid(),
  em timestamptz not null default now(),
  acao text not null,
  parametros jsonb
);

create or replace function odi_interno.eh_pesquisador() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.pesquisadores p where p.user_id = auth.uid() and p.ativo and p.termo_aceito_em is not null)
$$;
create or replace function odi_interno.eh_responsavel() returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.pesquisadores p where p.user_id = auth.uid() and p.ativo and p.termo_aceito_em is not null and p.papel = 'responsavel')
$$;
create or replace function odi_interno._registrar(p_acao text, p_parametros jsonb) returns void language sql security definer set search_path = public as $$
  insert into public.acessos (user_id, acao, parametros) values (auth.uid(), p_acao, p_parametros)
$$;

alter table public.pesquisadores enable row level security;
alter table public.unidades enable row level security;
alter table public.codificacoes enable row level security;
alter table public.decisoes enable row level security;
alter table public.acessos enable row level security;

drop policy if exists pesq_le_a_propria on public.pesquisadores;
create policy pesq_le_a_propria on public.pesquisadores for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists unidades_so_pesquisador on public.unidades;
create policy unidades_so_pesquisador on public.unidades for select to authenticated using ((select odi_interno.eh_pesquisador()));
drop policy if exists cod_le_as_proprias on public.codificacoes;
create policy cod_le_as_proprias on public.codificacoes for select to authenticated using (user_id = (select auth.uid()));
drop policy if exists decisoes_responsavel on public.decisoes;
create policy decisoes_responsavel on public.decisoes for select to authenticated using ((select odi_interno.eh_responsavel()));
drop policy if exists acessos_le_o_proprio on public.acessos;
create policy acessos_le_o_proprio on public.acessos for select to authenticated using (user_id = (select auth.uid()));
-- nenhuma política de escrita: só as funções abaixo (e o service role, na carga) escrevem

revoke all on public.pesquisadores, public.unidades, public.codificacoes, public.decisoes, public.acessos from anon;
revoke insert, update, delete on public.pesquisadores, public.unidades, public.codificacoes, public.decisoes, public.acessos from authenticated;

-- situação e termo: o usuário logado lê e grava só a própria linha (avisos intencionais do linter)
create or replace function public.minha_situacao() returns jsonb language sql stable security definer set search_path = public as $$
  select jsonb_build_object('convidado', p.user_id is not null, 'ativo', coalesce(p.ativo, false),
                            'termo_aceito', p.termo_aceito_em is not null, 'papel', p.papel, 'nome', p.nome)
  from (select auth.uid() as u) x left join public.pesquisadores p on p.user_id = x.u
$$;
create or replace function public.aceitar_termo() returns boolean language plpgsql security definer set search_path = public as $$
begin
  update public.pesquisadores set termo_aceito_em = now() where user_id = auth.uid() and ativo and termo_aceito_em is null;
  insert into public.acessos (user_id, acao) select auth.uid(), 'aceitou_termo' where exists (select 1 from public.pesquisadores where user_id = auth.uid());
  return exists (select 1 from public.pesquisadores where user_id = auth.uid() and termo_aceito_em is not null);
end $$;

-- unidades com a codificação do próprio usuário e quantos já codificaram (sem os valores dos outros)
create or replace function odi_interno.codificadores_por_unidade() returns table (unidade_id text, n bigint)
language sql stable security definer set search_path = public as $$
  select unidade_id, count(*) from public.codificacoes where mencao is not null group by unidade_id
$$;
create or replace function public.unidades_para_codificar(p_ator text default null, p_rede text default null, p_pendentes boolean default false)
returns table (id text, ator_id text, rede text, publicado_em timestamptz, tipo text, url text, texto text, transcricao text, transcricao_status text,
  mencao text, posicao text, enquadramento text, formato text, obs text, codificadores bigint)
language plpgsql stable security invoker set search_path = public as $$
begin
  if not odi_interno.eh_pesquisador() then raise exception 'acesso restrito a pesquisadores convidados com termo aceito'; end if;
  return query
    select u.id, u.ator_id, u.rede, u.publicado_em, u.tipo, u.url, u.texto, u.transcricao, u.transcricao_status,
           c.mencao, c.posicao, c.enquadramento, c.formato, c.obs, coalesce(k.n, 0)
    from public.unidades u
    left join public.codificacoes c on c.unidade_id = u.id and c.user_id = auth.uid()
    left join odi_interno.codificadores_por_unidade() k on k.unidade_id = u.id
    where (p_ator is null or p_ator = '' or u.ator_id = p_ator)
      and (p_rede is null or p_rede = '' or u.rede = p_rede)
      and (not coalesce(p_pendentes, false) or c.mencao is null or c.enquadramento is null or c.formato is null)
    order by u.ordem;
end $$;

-- grava uma ou mais dimensões; B vira 'nao_se_aplica' quando A não é acordo nem Gaza
create or replace function odi_interno._gravar(p_unidade text, p_dados jsonb) returns jsonb language plpgsql security definer set search_path = public as $$
declare r public.codificacoes; m text;
begin
  if not odi_interno.eh_pesquisador() then raise exception 'acesso restrito a pesquisadores convidados com termo aceito'; end if;
  if not exists (select 1 from public.unidades where id = p_unidade) then raise exception 'unidade não encontrada'; end if;
  if p_dados - array['mencao', 'posicao', 'enquadramento', 'formato', 'obs'] <> '{}'::jsonb then raise exception 'campo desconhecido'; end if;
  insert into public.codificacoes as c (unidade_id, user_id) values (p_unidade, auth.uid()) on conflict do nothing;
  select coalesce(p_dados ->> 'mencao', c.mencao) into m from public.codificacoes c where c.unidade_id = p_unidade and c.user_id = auth.uid();
  update public.codificacoes c set
    mencao = case when p_dados ? 'mencao' then p_dados ->> 'mencao' else c.mencao end,
    posicao = case when m is not null and m not in ('acordo', 'gaza') then 'nao_se_aplica'
                   when p_dados ? 'posicao' then p_dados ->> 'posicao'
                   when c.posicao = 'nao_se_aplica' then null else c.posicao end,
    enquadramento = case when p_dados ? 'enquadramento' then p_dados ->> 'enquadramento' else c.enquadramento end,
    formato = case when p_dados ? 'formato' then p_dados ->> 'formato' else c.formato end,
    obs = case when p_dados ? 'obs' then nullif(p_dados ->> 'obs', '') else c.obs end,
    atualizado_em = now()
  where c.unidade_id = p_unidade and c.user_id = auth.uid()
  returning * into r;
  return to_jsonb(r) - 'user_id';
end $$;
create or replace function public.codificar(p_unidade text, p_dados jsonb) returns jsonb language plpgsql security invoker set search_path = public as $$
begin
  if not odi_interno.eh_pesquisador() then raise exception 'acesso restrito a pesquisadores convidados com termo aceito'; end if;
  return odi_interno._gravar(p_unidade, p_dados);
end $$;

-- pares de codificação completos (as duas pessoas marcaram a dimensão), por dimensão
create or replace function odi_interno.pares() returns table (dimensao text, unidade_id text, a uuid, b uuid, va text, vb text)
language sql stable security definer set search_path = public as $$
  with v as (
    select c.unidade_id, c.user_id, d.dimensao, d.valor
    from public.codificacoes c
    cross join lateral (values ('mencao', c.mencao), ('posicao', c.posicao), ('enquadramento', c.enquadramento), ('formato', c.formato)) d(dimensao, valor)
    join public.pesquisadores p on p.user_id = c.user_id and p.ativo
    where d.valor is not null)
  select x.dimensao, x.unidade_id, x.user_id, y.user_id, x.valor, y.valor
  from v x join v y on y.unidade_id = x.unidade_id and y.dimensao = x.dimensao and x.user_id < y.user_id
$$;

-- kappa de Cohen por dimensão e por par de codificadores (só agregados: ninguém vê o código do outro)
create or replace function odi_interno.kappa() returns table (dimensao text, codificador_a text, codificador_b text, unidades bigint,
  concordancia_observada numeric, kappa numeric)
language sql stable security definer set search_path = public as $$
  -- B só conta quando os dois viram acordo ou Gaza em A: "não se aplica" já é divergência (ou concordância) de A
  with p as (select * from odi_interno.pares() where not (dimensao = 'posicao' and 'nao_se_aplica' in (va, vb))),
  obs as (select dimensao, a, b, count(*) n, avg((va = vb)::int)::numeric po from p group by 1, 2, 3),
  ma as (select dimensao, a, b, va v, count(*) q from p group by 1, 2, 3, 4),
  mb as (select dimensao, a, b, vb v, count(*) q from p group by 1, 2, 3, 4),
  esp as (select o.dimensao, o.a, o.b, coalesce(sum((ma.q::numeric / o.n) * (mb.q::numeric / o.n)), 0) pe
          from obs o left join ma on ma.dimensao = o.dimensao and ma.a = o.a and ma.b = o.b
          left join mb on mb.dimensao = o.dimensao and mb.a = o.a and mb.b = o.b and mb.v = ma.v
          group by 1, 2, 3)
  select o.dimensao, coalesce(pa.nome, 'codificador'), coalesce(pb.nome, 'codificador'), o.n, round(o.po, 4),
         case when e.pe >= 1 then null else round((o.po - e.pe) / (1 - e.pe), 4) end
  from obs o join esp e using (dimensao, a, b)
  left join public.pesquisadores pa on pa.user_id = o.a left join public.pesquisadores pb on pb.user_id = o.b
  order by array_position(array['mencao', 'posicao', 'enquadramento', 'formato'], o.dimensao), o.n desc
$$;
create or replace function public.concordancia() returns table (dimensao text, codificador_a text, codificador_b text, unidades bigint,
  concordancia_observada numeric, kappa numeric)
language plpgsql stable security invoker set search_path = public as $$
begin
  if not odi_interno.eh_pesquisador() then raise exception 'acesso restrito a pesquisadores convidados com termo aceito'; end if;
  perform odi_interno._registrar('concordancia', null);
  return query select * from odi_interno.kappa();
end $$;

-- progresso agregado: unidades com 0, 1 e 2+ codificações completas
create or replace function public.progresso() returns jsonb language plpgsql stable security invoker set search_path = public as $$
declare r jsonb;
begin
  if not odi_interno.eh_pesquisador() then raise exception 'acesso restrito a pesquisadores convidados com termo aceito'; end if;
  select jsonb_build_object(
    'unidades', (select count(*) from public.unidades),
    'minhas_completas', (select count(*) from public.codificacoes where user_id = auth.uid() and mencao is not null and posicao is not null and enquadramento is not null and formato is not null),
    'com_duas_ou_mais', (select count(*) from odi_interno.codificadores_por_unidade() where n >= 2),
    'codificadores', (select count(distinct user_id) from odi_interno.pares_usuarios()))
  into r;
  return r;
end $$;
create or replace function odi_interno.pares_usuarios() returns table (user_id uuid) language sql stable security definer set search_path = public as $$
  select distinct user_id from public.codificacoes where mencao is not null
$$;

-- divergências e decisão final: só o responsável (terceiro codificador)
create or replace function public.divergencias() returns table (unidade_id text, dimensao text, valor_a text, valor_b text, decisao text)
language plpgsql stable security invoker set search_path = public as $$
begin
  if not odi_interno.eh_responsavel() then raise exception 'só o responsável vê as divergências'; end if;
  return query select p.unidade_id, p.dimensao, p.va, p.vb, d.valor
    from odi_interno.pares() p left join public.decisoes d on d.unidade_id = p.unidade_id and d.dimensao = p.dimensao
    where p.va <> p.vb order by p.unidade_id, p.dimensao;
end $$;
create or replace function odi_interno._decidir(p_unidade text, p_dimensao text, p_valor text) returns void language plpgsql security definer set search_path = public as $$
begin
  if not odi_interno.eh_responsavel() then raise exception 'só o responsável decide'; end if;
  if p_dimensao = 'mencao' and p_valor not in ('acordo', 'gaza', 'nao_politica', 'sem_relacao')
     or p_dimensao = 'posicao' and p_valor not in ('favoravel', 'cetica', 'contraria', 'informativa', 'humanitaria', 'nao_se_aplica')
     or p_dimensao = 'enquadramento' and p_valor not in ('religioso', 'politico', 'humanitario', 'identitario', 'denuncia', 'nenhum')
     or p_dimensao = 'formato' and p_valor not in ('fala_propria', 'repost', 'legenda', 'convite', 'outro') then
    raise exception 'valor fora do livro de códigos';
  end if;
  insert into public.decisoes (unidade_id, dimensao, valor, decidido_por) values (p_unidade, p_dimensao, p_valor, auth.uid())
  on conflict (unidade_id, dimensao) do update set valor = excluded.valor, decidido_por = excluded.decidido_por, decidido_em = now();
  perform odi_interno._registrar('decidir', jsonb_build_object('unidade', p_unidade, 'dimensao', p_dimensao));
end $$;
create or replace function public.decidir(p_unidade text, p_dimensao text, p_valor text) returns void language plpgsql security invoker set search_path = public as $$
begin
  if not odi_interno.eh_responsavel() then raise exception 'só o responsável decide'; end if;
  perform odi_interno._decidir(p_unidade, p_dimensao, p_valor);
end $$;

-- código final por unidade e dimensão: o valor concordado pelos dois, ou a decisão do responsável; senão nulo
create or replace function odi_interno.final() returns table (unidade_id text, dimensao text, valor text, origem text)
language sql stable security definer set search_path = public as $$
  select u.id, d.dimensao,
         coalesce(dc.valor, case when bool_and(p.va = p.vb) and count(p.*) > 0 then min(p.va) end),
         case when dc.valor is not null then 'decisão' when bool_and(p.va = p.vb) and count(p.*) > 0 then 'concordância' else 'pendente' end
  from public.unidades u
  cross join (values ('mencao'), ('posicao'), ('enquadramento'), ('formato')) d(dimensao)
  left join odi_interno.pares() p on p.unidade_id = u.id and p.dimensao = d.dimensao
  left join public.decisoes dc on dc.unidade_id = u.id and dc.dimensao = d.dimensao
  group by u.id, d.dimensao, dc.valor
$$;
create or replace function public.resultado_final() returns table (unidade_id text, dimensao text, valor text, origem text)
language plpgsql stable security invoker set search_path = public as $$
begin
  if not odi_interno.eh_responsavel() then raise exception 'só o responsável exporta o resultado'; end if;
  return query select * from odi_interno.final();
end $$;

revoke execute on all functions in schema odi_interno from public, anon;
grant execute on all functions in schema odi_interno to authenticated;
revoke execute on function public.unidades_para_codificar(text, text, boolean), public.codificar(text, jsonb), public.concordancia(),
  public.progresso(), public.divergencias(), public.decidir(text, text, text), public.resultado_final() from public, anon;
grant execute on function public.unidades_para_codificar(text, text, boolean), public.codificar(text, jsonb), public.concordancia(),
  public.progresso(), public.divergencias(), public.decidir(text, text, text), public.resultado_final() to authenticated;
revoke execute on function public.minha_situacao(), public.aceitar_termo() from public, anon;
grant execute on function public.minha_situacao(), public.aceitar_termo() to authenticated;
