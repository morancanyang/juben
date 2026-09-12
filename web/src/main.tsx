import { Component, StrictMode, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './final.css'

class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  state={failed:false}
  static getDerivedStateFromError(){return {failed:true}}
  render(){return this.state.failed?<div className="empty-state"><h1>页面遇到一点问题</h1><p>已提交的调查仍保存在服务器。刷新可以重新载入。</p><button className="primary-button" onClick={()=>location.reload()}>重新载入</button></div>:this.props.children}
}
createRoot(document.getElementById('root')!).render(<StrictMode><ErrorBoundary><App/></ErrorBoundary></StrictMode>)
if('serviceWorker' in navigator && import.meta.env.PROD){navigator.serviceWorker.register('/sw.js').catch(()=>{})}
