import {
  Route,
  Routes,
} from 'react-router'

import PublicLayout from './layouts/PublicLayout'
import HomePage from './pages/HomePage'
import ItemPage from './pages/ItemPage'
import NotFoundPage from './pages/NotFoundPage'

import AdminLayout from './admin/layouts/AdminLayout'
import AdminHomePage from './admin/pages/AdminHomePage'
import AdminLoginPage from './admin/pages/AdminLoginPage'
import AdminItemsPage from './admin/pages/AdminItemsPage'
import AdminItemFormPage from './admin/pages/AdminItemFormPage'
import AdminCollectionsPage from './admin/pages/AdminCollectionsPage'
import AdminCollectionFormPage from './admin/pages/AdminCollectionFormPage'
import CollectionPage from "./pages/CollectionPage.tsx";


function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route
          path="/"
          element={<HomePage />}
        />

        <Route
          path="/c/:slug"
          element={<CollectionPage />}
        />
        <Route
          path="/items/:slug"
          element={<ItemPage />}
        />
        <Route
          path="/i/:publicId"
          element={<ItemPage />}
        />
        <Route
          path="*"
          element={<NotFoundPage />}
        />
      </Route>

      <Route
        path="/admin/login"
        element={<AdminLoginPage />}
      />

      <Route
        path="/admin"
        element={<AdminLayout />}
      >
        <Route
          index
          element={<AdminHomePage />}
        />
        <Route
          path="items"
          element={<AdminItemsPage />}
        />
        <Route
          path="items/new"
          element={<AdminItemFormPage />}
        />

        <Route
          path="items/:itemId"
          element={<AdminItemFormPage />}
        />
        <Route
          path="collections"
          element={<AdminCollectionsPage />}
        />
        <Route
          path="collections/new"
          element={<AdminCollectionFormPage />}
        />

        <Route
          path="collections/:collectionId"
          element={<AdminCollectionFormPage />}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}

export default App