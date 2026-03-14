import { mount } from 'svelte'
import './app.css'
import InteractiveViz from './InteractiveViz.svelte'

const app = mount(InteractiveViz, {
  target: document.getElementById('app'),
})

export default app
