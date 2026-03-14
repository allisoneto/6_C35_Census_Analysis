<script lang="ts">
  /** Current page for active link styling. */
  let { currentPage = 'main' } = $props<{ currentPage?: 'main' | 'interactive' }>()
</script>

<nav class="navbar">
  <a href="/" class:active={currentPage === 'main'}>PNG Viewer</a>
  <a href="/interactive.html" class:active={currentPage === 'interactive'}>Interactive D3</a>
</nav>

<style>
  .navbar {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #e0e0e0;
  }
  .navbar a {
    color: #4a90d9;
    text-decoration: none;
    font-size: 0.95rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  .navbar a:hover {
    text-decoration: underline;
    background: #f5f5f5;
  }
  .navbar a.active {
    font-weight: 600;
    color: #2a70b9;
    background: #e8f0fa;
    text-decoration: none;
  }
</style>
