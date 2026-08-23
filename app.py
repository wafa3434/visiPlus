def _login_screen(session):
    # استخدام أعمدة متساوية الأطراف لدفع المحتوى للوسط بدقة
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            # استخدام div مع خاصية text-align: center لتوسيط الصورة والعنوان قسراً
            st.markdown(
                """
                <div style="text-align: center; width: 100%;">
                    <img src="logo.jpeg" width="160" style="display: block; margin: 0 auto; border-radius: 8px;">
                </div>
                """, 
                unsafe_allow_html=True
            )
        except Exception:
            pass
            
        st.markdown(f"<h3 style='text-align: center; width: 100%; margin-top: 15px;'>{t['title']}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; width: 100%; color: gray;'>{t['subtitle']}</p>", unsafe_allow_html=True)
            
    st.divider()

    if st.session_state.get("pending_verification"):
        _, mid_v, _ = st.columns([1, 1.2, 1])
        with mid_v:
            st.info(f"{t['verify_msg']} **{st.session_state.get('demo_code')}**")
            with st.form("verify_form"):
                entered_code = st.text_input(t["code_input"], type="password")
                verify_submitted = st.form_submit_button(t["verify_btn"], width="stretch")

            if verify_submitted:
                if entered_code == str(st.session_state.get("demo_code")):
                    st.session_state.authenticated = True
                    st.session_state.pending_verification = False
                    st.success("تم التحقق بنجاح")
                    st.rerun()
                else:
                    st.error(t["invalid_code"])
        return

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.form("login_form"):
            username = st.text_input(t["username"])
            password = st.text_input(t["password"], type="password")
            submitted = st.form_submit_button(t["login_btn"], width="stretch")

        if submitted:
            user, result = attempt_login(session, username, password)
            if user is None:
                st.error(result)
            else:
                code = random.randint(1000, 9999)
                st.session_state.demo_code = code
                st.session_state.pending_verification = True
                st.session_state.temp_user_id = user.id
                st.session_state.temp_username = user.username
                st.session_state.temp_role = user.role.value
                st.rerun()
