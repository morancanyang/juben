import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, Check, Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { api, ApiError, type User } from '../api'

export function isSessionUser(value: unknown): value is User {
  const u = value as Partial<User> | null
  return !!u && typeof u.id === 'string' && typeof u.csrf === 'string' && !!u.csrf &&
    typeof u.nickname === 'string' && typeof u.guest === 'boolean' && !!u.preferences
}

type Props = { disabled: boolean; success: boolean; onAuthenticated: (user: User) => void }

/** Request state lives here; it never guesses when the cinematic transition should start. */
export default function AuthForm({ disabled, success, onAuthenticated }: Props) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState<'account' | 'guest' | null>(null)
  const [error, setError] = useState('')
  const [field, setField] = useState('')
  const [message, setMessage] = useState('')
  const request = useRef<AbortController | null>(null)
  const live = useRef(true)
  const completed = useRef(false)
  const alert = useRef<HTMLParagraphElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const locked = disabled || success || !!busy

  useEffect(() => { live.current = true; return () => { live.current = false; request.current?.abort() } }, [])
  useEffect(() => { if (error) alert.current?.focus() }, [error])

  const switchMode = () => {
    if (locked) return
    setMode(mode === 'login' ? 'register' : 'login')
    setError(''); setField(''); setMessage(''); setPassword(''); setConfirmation(''); setVisible(false)
    heading.current?.focus()
  }

  const submit = async (guest = false) => {
    if (request.current || locked || completed.current) return
    setError(''); setField(''); setMessage('')
    const name = username.trim()
    if (!guest) {
      if (!/^[a-zA-Z0-9_]{3,32}$/.test(name)) {
        setField('username'); setError('用户名须为 3–32 位英文字母、数字或下划线。'); return
      }
      if (password.length < 8 || password.length > 128) {
        setField('password'); setError('密码须为 8–128 位字符。'); return
      }
      if (mode === 'register' && password !== confirmation) {
        setField('confirmation'); setError('两次输入的密码不一致，请重新确认。'); return
      }
    }
    const controller = new AbortController()
    request.current = controller; setBusy(guest ? 'guest' : 'account')
    let timedOut = false
    const timeout = window.setTimeout(() => { timedOut = true; controller.abort() }, 15000)
    try {
      const data = await api(`/api/v1/auth/${guest ? 'guest' : mode}`, {
        method: 'POST', body: JSON.stringify(guest ? {} : { username: name, password }), signal: controller.signal,
      })
      if (!live.current) return
      // Registration may create an account without issuing a session on another deployment.
      let user = data.user
      if (!isSessionUser(user)) user = (await api('/api/v1/me', { signal: controller.signal })).user
      if (!live.current) return
      if (isSessionUser(user) && (guest || !user.guest)) {
        completed.current = true
        setPassword(''); setConfirmation('')
        onAuthenticated(user)
      } else if (mode === 'register' && !guest) {
        setMode('login'); setPassword(''); setConfirmation(''); setVisible(false)
        setMessage('档案已建立，请使用刚才的用户名和密码登录。')
        heading.current?.focus()
      } else {
        setError('服务未建立有效登录会话，请重新登录。')
      }
    } catch (e) {
      if (!live.current) return
      setError(timedOut ? '连接超时，请检查网络后重试。' : e instanceof ApiError ? e.message : '网络连接中断，未能确认身份。请检查连接后重试。')
    } finally {
      clearTimeout(timeout)
      if (request.current === controller) request.current = null
      if (live.current) setBusy(null)
    }
  }

  const onSubmit = (event: FormEvent) => { event.preventDefault(); void submit() }
  return <div className="cinema-form-content" data-mode={mode}>
    <div className="cinema-form-intro">
      <span className="cinema-eyebrow">{mode === 'login' ? 'PERSONNEL ACCESS / 身份核验' : 'NEW INVESTIGATOR / 档案登记'}</span>
      <h2 ref={heading} tabIndex={-1}>{mode === 'login' ? '灯还亮着。' : '建立你的调查档案'}</h2>
      <p>{mode === 'login' ? '一份未结的卷宗，正等你翻开。' : '为每一次发现，留下你的名字。'}</p>
    </div>
    <form onSubmit={onSubmit} noValidate aria-label={mode === 'login' ? '登录' : '注册'} aria-busy={!!busy}>
      <fieldset disabled={locked}>
        <div className="cinema-field">
          <label htmlFor="case-username">用户名 <span>USERNAME</span></label>
          <input id="case-username" name="username" value={username} onChange={e => setUsername(e.target.value)}
            autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={32} required
            placeholder="你的调查员代号" aria-invalid={field === 'username'} aria-describedby={field === 'username' ? 'auth-error' : mode === 'register' ? 'username-hint' : undefined}/>
          {mode === 'register' && <small id="username-hint">3–32 位英文字母、数字或下划线</small>}
        </div>
        <div className="cinema-field">
          <label htmlFor="case-password">密码 <span>PASSWORD</span></label>
          <div className="cinema-password">
            <input id="case-password" name="password" type={visible ? 'text' : 'password'} value={password}
              onChange={e => setPassword(e.target.value)} autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder={mode === 'login' ? '输入你的密码' : '设置 8–128 位密码'} minLength={8} maxLength={128} required
              aria-invalid={field === 'password'} aria-describedby={field === 'password' ? 'auth-error' : undefined}/>
            <button type="button" className="cinema-eye" onClick={() => setVisible(!visible)} aria-label={visible ? '隐藏密码' : '显示密码'} aria-pressed={visible}>
              {visible ? <EyeOff size={18}/> : <Eye size={18}/>}</button>
          </div>
        </div>
        <div className={`cinema-confirm ${mode === 'register' ? 'is-open' : ''}`} aria-hidden={mode !== 'register'} inert={mode !== 'register'}>
          <div><div className="cinema-field">
            <label htmlFor="case-confirmation">确认密码 <span>CONFIRM PASSWORD</span></label>
            <input id="case-confirmation" name="confirmation" type={visible ? 'text' : 'password'} value={confirmation}
              onChange={e => setConfirmation(e.target.value)} autoComplete="new-password" placeholder="再次输入密码"
              maxLength={128} required={mode === 'register'} disabled={mode !== 'register' || locked}
              aria-invalid={field === 'confirmation'} aria-describedby={field === 'confirmation' ? 'auth-error' : undefined}/>
          </div></div>
        </div>
        {error && <p id="auth-error" className="cinema-error" role="alert" ref={alert} tabIndex={-1}><span>提示 / </span>{error}</p>}
        {message && <p className="cinema-message" role="status">{message}</p>}
        <button className="cinema-submit" type="submit">
          <span>{success ? '身份已确认' : busy === 'account' ? '正在核验身份…' : mode === 'login' ? '进入调查' : '建立档案'}</span>
          {success ? <Check size={19}/> : busy === 'account' ? <LoaderCircle className="cinema-spinning" size={19}/> : <ArrowRight size={19}/>}</button>
        <button type="button" className="cinema-mode" onClick={switchMode}>
          {mode === 'login' ? <>第一次来到这里？<strong>建立档案</strong></> : <><ArrowLeft size={14}/> 返回登录</>}</button>
        {mode === 'login' && <div className="cinema-guest-row"><span/><button className="cinema-guest" type="button" onClick={() => void submit(true)}>
          {busy === 'guest' ? '正在建立游客档案…' : '先以游客身份调查'}</button><span/></div>}
      </fieldset>
    </form>
    <p className="cinema-footnote">{mode === 'login' ? '单人沉浸推理 · 调查进度自动保存' : '档案仅属于你，真相由你亲自发现。'}</p>
  </div>
}
