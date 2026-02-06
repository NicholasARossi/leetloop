drop extension if exists "pg_net";

drop policy if exists "review_queue_delete_policy" on "public"."review_queue";

drop policy if exists "review_queue_insert_policy" on "public"."review_queue";

drop policy if exists "review_queue_select_policy" on "public"."review_queue";

drop policy if exists "review_queue_update_policy" on "public"."review_queue";

drop policy if exists "skill_scores_delete_policy" on "public"."skill_scores";

drop policy if exists "skill_scores_insert_policy" on "public"."skill_scores";

drop policy if exists "skill_scores_select_policy" on "public"."skill_scores";

drop policy if exists "skill_scores_update_policy" on "public"."skill_scores";

drop policy if exists "submission_notes_delete_policy" on "public"."submission_notes";

drop policy if exists "submission_notes_insert_policy" on "public"."submission_notes";

drop policy if exists "submission_notes_select_policy" on "public"."submission_notes";

drop policy if exists "submission_notes_update_policy" on "public"."submission_notes";

drop policy if exists "submissions_delete_policy" on "public"."submissions";

drop policy if exists "submissions_insert_policy" on "public"."submissions";

drop policy if exists "submissions_select_policy" on "public"."submissions";

drop policy if exists "submissions_update_policy" on "public"."submissions";

drop policy if exists "user_settings_insert_policy" on "public"."user_settings";

drop policy if exists "user_settings_select_policy" on "public"."user_settings";

drop policy if exists "user_settings_update_policy" on "public"."user_settings";

alter table "public"."review_queue" drop constraint if exists "review_queue_user_problem_unique";

drop function if exists "public"."migrate_guest_to_auth"(p_guest_id uuid, p_auth_id uuid);

drop index if exists "public"."review_queue_user_problem_unique";


  create policy "Allow anonymous insert"
  on "public"."review_queue"
  as permissive
  for insert
  to public
with check (true);



  create policy "Allow anonymous select"
  on "public"."review_queue"
  as permissive
  for select
  to public
using (true);



  create policy "Allow anonymous update"
  on "public"."review_queue"
  as permissive
  for update
  to public
using (true);



  create policy "Allow anonymous insert"
  on "public"."skill_scores"
  as permissive
  for insert
  to public
with check (true);



  create policy "Allow anonymous select"
  on "public"."skill_scores"
  as permissive
  for select
  to public
using (true);



  create policy "Allow anonymous update"
  on "public"."skill_scores"
  as permissive
  for update
  to public
using (true);



  create policy "Users can delete own notes"
  on "public"."submission_notes"
  as permissive
  for delete
  to public
using ((auth.uid() = user_id));



  create policy "Users can insert own notes"
  on "public"."submission_notes"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can update own notes"
  on "public"."submission_notes"
  as permissive
  for update
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own notes"
  on "public"."submission_notes"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "Allow anonymous insert"
  on "public"."submissions"
  as permissive
  for insert
  to public
with check (true);



  create policy "Allow anonymous select own"
  on "public"."submissions"
  as permissive
  for select
  to public
using (true);



