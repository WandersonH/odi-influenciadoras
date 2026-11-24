-- Teste da área interna (rodar depois de 00 e da migração). Saída esperada: linhas "ok ..." e nenhum "FALHOU".
\set ON_ERROR_STOP off
insert into auth.users values ('00000000-0000-0000-0000-00000000000a','a@x'),('00000000-0000-0000-0000-00000000000b','b@x'),('00000000-0000-0000-0000-00000000000c','c@x'),('00000000-0000-0000-0000-00000000000d','d@x');
insert into public.pesquisadores (user_id, nome, papel) values ('00000000-0000-0000-0000-00000000000a','Ana','codificador'),('00000000-0000-0000-0000-00000000000b','Bia','codificador'),('00000000-0000-0000-0000-00000000000c','Resp','responsavel');
insert into public.unidades (id, ator_id, rede, texto, ordem) select 'tiktok:'||i, 'mariam-chami', 'tiktok', 'post '||i, md5('tiktok:'||i) from generate_series(1,10) i;
set role authenticated;
-- não convidado
set request.jwt.claim.sub = '00000000-0000-0000-0000-00000000000d';
select case when (select count(*) from public.unidades)=0 then 'ok não convidado vê 0 unidades' else 'FALHOU não convidado' end;
-- convidado sem termo
set request.jwt.claim.sub = '00000000-0000-0000-0000-00000000000a';
select case when (select count(*) from public.unidades)=0 then 'ok sem termo vê 0' else 'FALHOU sem termo' end;
select case when public.aceitar_termo() then 'ok termo aceito' else 'FALHOU termo' end;
select case when (select count(*) from public.unidades_para_codificar())=10 then 'ok com termo vê 10' else 'FALHOU com termo' end;
-- Ana codifica 1..10: menções alternadas
select public.codificar('tiktok:'||i, jsonb_build_object('mencao', case when i<=4 then 'gaza' else 'sem_relacao' end, 'enquadramento', case when i<=4 then 'humanitario' else 'nenhum' end, 'formato','fala_propria')) from generate_series(1,10) i \g /dev/null
select case when (select count(*) from public.codificacoes where posicao='nao_se_aplica')=6 then 'ok B automático = não se aplica (6)' else 'FALHOU B automático' end;
select public.codificar('tiktok:'||i, '{"posicao":"humanitaria"}') from generate_series(1,4) i \g /dev/null
select case when (select count(*) from public.codificacoes where posicao='humanitaria')=4 then 'ok B gravado' else 'FALHOU B' end;
-- valor fora do livro e campo desconhecido
do $$ begin perform public.codificar('tiktok:1', '{"mencao":"inventado"}'); raise notice 'FALHOU aceitou valor fora do livro'; exception when others then raise notice 'ok recusou valor fora do livro'; end $$;
do $$ begin perform public.codificar('tiktok:1', '{"xyz":"1"}'); raise notice 'FALHOU aceitou campo desconhecido'; exception when others then raise notice 'ok recusou campo desconhecido'; end $$;
-- escrita direta negada
do $$ begin insert into public.codificacoes (unidade_id, mencao) values ('tiktok:1','acordo'); raise notice 'FALHOU escrita direta'; exception when others then raise notice 'ok escrita direta negada'; end $$;
-- Bia codifica: concorda em 8 de 10 na menção
set request.jwt.claim.sub = '00000000-0000-0000-0000-00000000000b';
select public.aceitar_termo() \g /dev/null
select case when (select count(*) from public.codificacoes)=0 then 'ok Bia não vê os códigos da Ana' else 'FALHOU cegueira' end;
select public.codificar('tiktok:'||i, jsonb_build_object('mencao', case when i<=2 then 'acordo' when i<=4 then 'gaza' else 'sem_relacao' end, 'enquadramento', case when i<=4 then 'humanitario' else 'nenhum' end, 'formato','fala_propria')) from generate_series(1,10) i \g /dev/null
select dimensao, unidades, concordancia_observada, kappa from public.concordancia();
do $$ begin perform * from public.divergencias(); raise notice 'FALHOU codificador viu divergências'; exception when others then raise notice 'ok codificador não vê divergências'; end $$;
select public.progresso();
-- responsável vê divergências e decide
set request.jwt.claim.sub = '00000000-0000-0000-0000-00000000000c';
select public.aceitar_termo() \g /dev/null
select count(*) as divergencias from public.divergencias();
select public.decidir('tiktok:1','mencao','acordo');
do $$ begin perform public.decidir('tiktok:1','mencao','xxx'); raise notice 'FALHOU decisão fora do livro'; exception when others then raise notice 'ok decisão fora do livro recusada'; end $$;
select origem, count(*) from public.resultado_final() where dimensao='mencao' group by 1 order by 1;
-- anon
reset request.jwt.claim.sub; set role anon;
do $$ begin perform public.unidades_para_codificar(); raise notice 'FALHOU anon'; exception when others then raise notice 'ok anon negado'; end $$;
reset role;
